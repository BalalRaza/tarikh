const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export interface EventSummary {
  id: string;
  event_type: string;
  importance: number;
  date_ah: number | null;
  date_ce: number | null;
  sort_key: number | null;
  title_en: string;
  title_ar: string;
  summary_en: string;
  loc_lat: number | null;
  loc_lng: number | null;
}

export interface EventsResponse {
  events: EventSummary[];
  next_cursor: string | null;
  total: number;
}

export interface GetEventsParams {
  importance?: number[];
  type?: string;
  q?: string;
  date_from?: number;
  date_to?: number;
  has_location?: boolean;
  cursor?: string;
  limit?: number;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export async function getEvents(params: GetEventsParams = {}): Promise<EventsResponse> {
  const q = new URLSearchParams();
  if (params.importance?.length) q.set('importance', params.importance.join(','));
  if (params.type) q.set('type', params.type);
  if (params.q) q.set('q', params.q);
  if (params.date_from != null) q.set('date_from', String(params.date_from));
  if (params.date_to != null) q.set('date_to', String(params.date_to));
  if (params.has_location != null) q.set('has_location', String(params.has_location));
  if (params.cursor) q.set('cursor', params.cursor);
  if (params.limit != null) q.set('limit', String(params.limit));
  return apiFetch<EventsResponse>(`/api/v1/events?${q.toString()}`);
}

export async function getEvent(id: string): Promise<unknown> {
  return apiFetch(`/api/v1/events/${encodeURIComponent(id)}`);
}

export async function getStats(): Promise<unknown> {
  return apiFetch('/api/v1/stats');
}

/** Fetch all pages, calling onPage for each batch. Stop early if onPage returns false. */
export async function fetchAllEvents(
  params: Omit<GetEventsParams, 'cursor'>,
  onPage: (events: EventSummary[], total: number) => boolean | void,
): Promise<void> {
  let cursor: string | null = null;
  do {
    const res = await getEvents({ ...params, cursor: cursor ?? undefined });
    const cont = onPage(res.events, res.total);
    if (cont === false) break;
    cursor = res.next_cursor;
  } while (cursor != null);
}
