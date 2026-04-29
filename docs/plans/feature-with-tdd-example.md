# 功能开发计划 (TDD 示例)

为价格监控系统添加邮件通知功能。

---

## Task 1: 添加价格提醒邮件服务

**问题描述:**
当商品价格低于设定阈值时，需要发送邮件通知用户。

**修复方案:**
创建邮件服务模块，支持：
- SMTP 配置管理
- 邮件模板渲染
- 发送重试机制

**修改文件:**
- `app/services/email_service.py`
- `app/models/email_config.py`
- `tests/test_email_service.py`

**TDD 要求:**
```
先写测试，再实现功能。遵循 Red-Green-Refactor:

1. RED: 写失败的测试
   - test_send_price_alert_email_success
   - test_send_email_with_retry_on_failure
   - test_render_email_template

2. GREEN: 写最小代码通过测试

3. REFACTOR: 清理代码
```

**验收标准:**
- [ ] `test_send_price_alert_email_success` 通过
- [ ] `test_send_email_with_retry_on_failure` 通过
- [ ] `test_render_email_template` 通过
- [ ] 发送失败时自动重试 3 次
- [ ] 邮件内容包含商品名称、原价、新价、降价幅度

---

## Task 2: 集成价格告警触发器

**问题描述:**
在价格检查逻辑中，当价格低于阈值时触发邮件通知。

**修复方案:**
在 `check_price_alerts()` 函数中：
1. 获取商品的价格历史
2. 计算降价幅度
3. 如果超过阈值，调用邮件服务

**修改文件:**
- `app/services/alert_service.py`
- `tests/test_alert_service.py`

**TDD 要求:**
```
必须先写测试:

1. RED:
   - test_price_drop_triggers_alert
   - test_no_alert_when_above_threshold
   - test_alert_not_sent_twice_for_same_drop

2. GREEN: 实现功能

3. REFACTOR: 优化告警逻辑
```

**验收标准:**
- [ ] 降价超过阈值时触发告警
- [ ] 降价未达阈值时不触发
- [ ] 同一降价不会重复发送告警
- [ ] 告警记录持久化到数据库

---

## Task 3: 添加邮件配置管理 API

**问题描述:**
用户需要配置自己的 SMTP 邮件发送设置。

**修复方案:**
添加 REST API 端点：
- `GET /api/email-config` - 获取当前配置
- `PUT /api/email-config` - 更新配置
- `POST /api/email-config/test` - 发送测试邮件

**修改文件:**
- `app/api/email_config.py`
- `tests/test_email_config_api.py`

**TDD 要求:**
```
API 测试驱动开发:

1. RED: 写 API 测试
   - test_get_email_config_returns_current_settings
   - test_update_email_config_saves_to_db
   - test_test_email_endpoint_sends_email

2. GREEN: 实现 API

3. REFACTOR: 统一错误处理
```

**验收标准:**
- [ ] 获取配置返回正确的 SMTP 设置
- [ ] 更新配置后持久化成功
- [ ] 测试邮件端点发送成功
- [ ] 无效配置返回 400 错误

---

## 执行顺序

1. Task 1 (邮件服务基础)
2. Task 2 (告警集成)
3. Task 3 (配置 API)

## 风险

- Task 1 是基础，失败会影响后续任务
- Task 2 需要与现有爬虫逻辑集成
- Task 3 涉及安全敏感的配置数据

## 依赖

- Task 2 依赖 Task 1 完成
- Task 3 独立于其他任务
