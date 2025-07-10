'use client';

import useSWR from 'swr';
import { fetcher } from '@/lib/fetcher';

interface Row {
  id: number;
  name: string;
  avg_score: number;
  last_eval: string;
}

export default function LeaderboardPage() {
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const { data, error, isLoading } = useSWR<Row[]>(
    `${api}/v0/leaderboard?limit=50`,
    fetcher,
    { refreshInterval: 60_000 } // 60 s
  );

  if (isLoading) return <p>Loading…</p>;
  if (error) return <p className="text-red-500">Error: {error.message}</p>;

  return (
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Model</th>
          <th>Score</th>
          <th>Last eval (UTC)</th>
        </tr>
      </thead>
      <tbody>
        {data?.map((row, i) => (
          <tr key={row.id}>
            <td>{i + 1}</td>
            <td>{row.name}</td>
            <td>{row.avg_score.toFixed(3)}</td>
            <td>{new Date(row.last_eval).toISOString().replace('T', ' ').slice(0, 19)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
