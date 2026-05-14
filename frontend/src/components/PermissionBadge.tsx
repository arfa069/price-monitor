import { Tooltip } from "antd";
import type { PermissionLevel } from "@/types";

const BADGE_CLASS: Record<NonNullable<PermissionLevel>, string> = {
  manage: "permission-badge permission-badge--manage",
  edit: "permission-badge permission-badge--edit",
  read: "permission-badge permission-badge--read",
};

const BADGE_LABEL: Record<NonNullable<PermissionLevel>, string> = {
  manage: "可管理",
  edit: "可编辑",
  read: "只读",
};

interface Props {
  level: PermissionLevel;
  disabledReason?: string;
}

export function PermissionBadge({ level, disabledReason }: Props) {
  if (!level) return null;

  const badge = (
    <span className={BADGE_CLASS[level]}>{BADGE_LABEL[level]}</span>
  );
  if (!disabledReason) return badge;
  return <Tooltip title={disabledReason}>{badge}</Tooltip>;
}
