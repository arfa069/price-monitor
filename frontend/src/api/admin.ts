import api from "./client";
import type {
  ResourcePermission,
  ResourcePermissionGrant,
  ResourcePermissionListResponse,
  ResourcePermissionUpdate,
  User,
} from "@/types";

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role: string;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  role?: string;
  is_active?: boolean;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLog {
  id: number;
  actor_user_id: number | null;
  action: string;
  target_type: string | null;
  target_id: number | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export const adminApi = {
  listUsers: async (params: {
    page?: number;
    page_size?: number;
    search?: string;
    role?: string;
  }): Promise<UserListResponse> => {
    const response = await api.get<UserListResponse>("/admin/users", {
      params,
    });
    return response.data;
  },

  createUser: async (data: UserCreate): Promise<User> => {
    const response = await api.post<User>("/admin/users", data);
    return response.data;
  },

  updateUser: async (id: number, data: UserUpdate): Promise<User> => {
    const response = await api.patch<User>(`/admin/users/${id}`, data);
    return response.data;
  },

  deleteUser: async (id: number): Promise<void> => {
    await api.delete(`/admin/users/${id}`);
  },

  getAuditLogs: async (params: {
    page?: number;
    page_size?: number;
    actor_user_id?: number;
    action?: string;
  }): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>("/admin/audit-logs", {
      params,
    });
    return response.data;
  },

  listResourcePermissions: async (params: {
    user_id?: number;
    resource_type?: string;
    page?: number;
    page_size?: number;
  }): Promise<ResourcePermissionListResponse> => {
    const response = await api.get<ResourcePermissionListResponse>(
      "/admin/resource-permissions",
      { params },
    );
    return response.data;
  },

  grantResourcePermission: async (
    grant: ResourcePermissionGrant,
  ): Promise<{ granted: number }> => {
    const response = await api.post<{ granted: number }>(
      "/admin/resource-permissions",
      grant,
    );
    return response.data;
  },

  revokeResourcePermission: async (id: number): Promise<void> => {
    await api.delete(`/admin/resource-permissions/${id}`);
  },

  updateResourcePermission: async (
    id: number,
    data: ResourcePermissionUpdate,
  ): Promise<ResourcePermission> => {
    const response = await api.patch<ResourcePermission>(
      `/admin/resource-permissions/${id}`,
      data,
    );
    return response.data;
  },
};
