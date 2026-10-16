import type { PostStatus } from "./api";

export const NETWORK_LABELS: Record<string, string> = { telegram: "Telegram channel" };

export const STATUS_LABELS: Record<PostStatus, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  publishing: "Publishing",
  published: "Published",
  failed: "Failed",
};

export const LANGUAGES: Record<string, string> = { uz: "O'zbekcha", en: "English" };

// Telegram Bot API limits.
export const TEXT_LIMIT = 4096;
export const CAPTION_LIMIT = 1024;
export const MEDIA_LIMIT = 10;

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
