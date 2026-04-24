"""
Real Database Integration Tests
================================
使用真实 PostgreSQL 数据库测试核心 CRUD 操作。

运行方式：
    pytest tests/test_integration_realdb.py -v -s

问题修复：
- 移除 cleanup fixture，避免 session 冲突
- 使用独立 session 模式
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.main import app
from app.models.product import Product
from app.models.user import User

# =============================================================================
# Helper: run in isolated session
# =============================================================================

async def run_in_session(fn):
    """在独立 session 中执行，失败时回滚"""
    async with AsyncSessionLocal() as session:
        try:
            return await fn(session)
        except Exception:
            await session.rollback()
            raise


# =============================================================================
# Config API Tests
# =============================================================================

class TestConfigApiRealDb:
    """用户配置 API 真实数据库测试"""

    @pytest.mark.asyncio
    async def test_get_config_returns_existing_user(self):
        """GET /config 返回已存在的用户配置"""

        async def _check(session):
            result = await session.execute(select(User).where(User.id == 1))
            return result.scalar_one_or_none()

        await run_in_session(_check)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/config")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        print(f"[Config-01] PASS: GET /config returns user id={data['id']}")

    @pytest.mark.asyncio
    async def test_update_crawl_cron_saves_to_db(self):
        """PATCH /config 更新 cron 并持久化"""
        new_cron = "0 10 * * *"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch("/config", json={"crawl_cron": new_cron})

        assert response.status_code == 200
        data = response.json()
        assert data["crawl_cron"] == new_cron

        # 验证数据库实际已更新
        async def _verify(session):
            result = await session.execute(select(User).where(User.id == 1))
            user = result.scalar_one()
            return user.crawl_cron

        saved_cron = await run_in_session(_verify)
        assert saved_cron == new_cron
        print(f"[Config-02] PASS: cron update persisted: {new_cron}")


# =============================================================================
# Product CRUD API Tests
# =============================================================================

class TestProductCrudApiRealDb:
    """商品 CRUD API 真实数据库测试"""

    @pytest.mark.asyncio
    async def test_create_and_read_product(self):
        """创建商品并读取验证"""
        import uuid
        test_url = f"https://item.jd.com/test_{uuid.uuid4().hex[:8]}.html"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 创建
            create_resp = await client.post("/products", json={
                "platform": "jd",
                "url": test_url,
                "title": "集成测试商品",
                "active": True,
            })

        assert create_resp.status_code == 200
        data = create_resp.json()
        assert data["platform"] == "jd"
        assert data["url"] == test_url
        product_id = data["id"]

        # 验证数据库存在
        async def _verify(session):
            result = await session.execute(select(Product).where(Product.url == test_url))
            return result.scalar_one_or_none()

        product = await run_in_session(_verify)
        assert product is not None
        assert product.title == "集成测试商品"

        # 清理
        async def _cleanup(session):
            await session.execute(delete(Product).where(Product.id == product_id))
            await session.commit()

        await _cleanup(session) if (session := None) is None else await _cleanup(session)
        # 简化清理逻辑
        async with AsyncSessionLocal() as sess:
            await sess.execute(delete(Product).where(Product.id == product_id))
            await sess.commit()

        print(f"[Product-01] PASS: created and verified product id={product_id}")

    @pytest.mark.asyncio
    async def test_update_product_title(self):
        """更新商品 title"""
        import uuid
        test_url = f"https://item.jd.com/test_{uuid.uuid4().hex[:8]}.html"
        product_id = None

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 创建
                create_resp = await client.post("/products", json={
                    "platform": "jd",
                    "url": test_url,
                    "title": "原始标题",
                })
                product_id = create_resp.json()["id"]

                # 更新
                response = await client.patch(f"/products/{product_id}", json={
                    "title": "更新后的标题",
                })

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "更新后的标题"
            print("[Product-02] PASS: product title updated")

        finally:
            # 清理
            if product_id:
                async with AsyncSessionLocal() as sess:
                    await sess.execute(delete(Product).where(Product.id == product_id))
                    await sess.commit()

    @pytest.mark.asyncio
    async def test_delete_product(self):
        """删除商品"""
        import uuid
        test_url = f"https://item.jd.com/test_{uuid.uuid4().hex[:8]}.html"
        product_id = None

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 创建
                create_resp = await client.post("/products", json={
                    "platform": "jd",
                    "url": test_url,
                    "title": "待删除商品",
                })
                product_id = create_resp.json()["id"]

                # 删除
                response = await client.delete(f"/products/{product_id}")

            assert response.status_code == 200
            assert "message" in response.json()

            # 验证数据库已删除
            async def _verify(session):
                result = await session.execute(select(Product).where(Product.id == product_id))
                return result.scalar_one_or_none()

            product = await run_in_session(_verify)
            assert product is None
            print("[Product-03] PASS: product deleted")

        finally:
            # 清理（如果删除失败）
            if product_id:
                async with AsyncSessionLocal() as sess:
                    await sess.execute(delete(Product).where(Product.id == product_id))
                    await sess.commit()


# =============================================================================
# Pagination API Tests
# =============================================================================

class TestPaginationApiRealDb:
    """分页查询 API 测试"""

    @pytest.mark.asyncio
    async def test_pagination_defaults_to_15(self):
        """默认每页 15 条"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/products")

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 15
        assert data["page"] == 1
        print(f"[Pagination-01] PASS: default page_size=15, total={data['total']}")

    @pytest.mark.asyncio
    async def test_pagination_explicit_size(self):
        """显式 size 参数"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/products?page=1&size=5")

        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 5
        assert data["has_next"] is not None
        print("[Pagination-02] PASS: explicit size=5 works")

    @pytest.mark.asyncio
    async def test_pagination_out_of_range_returns_empty(self):
        """页码超出范围返回空列表"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/products?page=99999")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["has_next"] is False
        print("[Pagination-03] PASS: out of range returns empty items")


# =============================================================================
# Batch Operations Tests
# =============================================================================

class TestBatchOperationsRealDb:
    """批量操作真实数据库"""

    @pytest.mark.asyncio
    async def test_batch_create(self):
        """批量创建多个商品"""
        import uuid

        items = [
            {"platform": "jd", "url": f"https://item.jd.com/test_batch_{uuid.uuid4().hex[:4]}_1.html"},
            {"platform": "jd", "url": f"https://item.jd.com/test_batch_{uuid.uuid4().hex[:4]}_2.html"},
            {"platform": "jd", "url": f"https://item.jd.com/test_batch_{uuid.uuid4().hex[:4]}_3.html"},
        ]
        created_ids = []

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/products/batch-create", json={"items": items})

            assert response.status_code == 200
            results = response.json()
            assert len(results) == 3

            success_count = sum(1 for r in results if r.get("success"))
            assert success_count >= 2  # 至少 2 个成功

            # 收集成功的 ID
            created_ids = [r.get("id") for r in results if r.get("success")]
            print(f"[Batch-01] PASS: batch create {success_count}/{len(items)} succeeded")

        finally:
            # 清理
            if created_ids:
                async with AsyncSessionLocal() as sess:
                    for pid in created_ids:
                        await sess.execute(delete(Product).where(Product.id == pid))
                    await sess.commit()


# =============================================================================
# Summary
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def print_summary():
    """打印测试摘要"""
    yield
    print("\n" + "=" * 70)
    print("Real Database Integration Tests Complete")
    print("=" * 70)
