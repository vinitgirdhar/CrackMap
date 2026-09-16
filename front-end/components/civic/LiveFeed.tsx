"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { getPipelineEvents } from "@/lib/api";
import { useNow } from "@/lib/hooks/useNow";
import type { PipelineEvent } from "@/lib/types";
import { AuditTimeline } from "./AuditTimeline";

interface LiveFeedProps {
  isActive: boolean;
  limit?: number;
}

/** Board-wide activity stream: every stage transition across every case. */
export function LiveFeed({ isActive, limit = 14 }: LiveFeedProps) {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const now = useNow(1000, isActive);

  const load = useCallback(async () => {
    try {
      setEvents(await getPipelineEvents(limit));
    } catch {
      // The board already surfaces connection problems; a stale feed is fine.
    }
  }, [limit]);

  useEffect(() => {
    if (!isActive) return;
    // The first poll is queued rather than run inline, so state only ever
    // changes from a callback the external system drives — never from the
    // effect body itself (React compiler lint), and a mount renders once.
    const first = setTimeout(load, 0);
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void load();
    }, 3000);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, [isActive, load]);

  return (
    <section className="civic-panel live-feed">
      <header className="civic-panel-head">
        <div>
          <h4>
            <Activity size={17} />
            Live pipeline activity
          </h4>
          <p>Persisted audit events, including the transitions nobody clicked.</p>
        </div>
      </header>
      <div className="live-feed-scroll">
        {/* The endpoint already returns newest-first, which is the order a feed
            wants — unlike a single case's timeline, which reads oldest-first. */}
        <AuditTimeline events={events} now={now} compact />
      </div>
    </section>
  );
}
