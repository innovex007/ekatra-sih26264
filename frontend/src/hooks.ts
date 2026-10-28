import { useEffect, useState } from "react";
import { api } from "./api";

export interface Meta {
  bureaus: { id: number; name: string }[]; regions: string[]; categories: string[]; statuses: string[];
  interlock_mode: string; finding_topics: string[]; finding_verdicts: string[]; resolver_method: string; seed_date: string; min_reason_chars: number;
}
let cache: Meta | null = null;

export function useMeta(): Meta | null {
  const [m, setM] = useState<Meta | null>(cache);
  useEffect(() => { if (!cache) api<Meta>("/meta").then((x) => { cache = x; setM(x); }).catch(() => {}); }, []);
  return m;
}
export const clearMetaCache = () => { cache = null; };
