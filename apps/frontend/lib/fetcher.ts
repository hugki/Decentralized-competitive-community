export async function fetcher<T = unknown>(url: string): Promise<T> {
    const res = await fetch(url, { next: { revalidate: 0 } }); // 常に network
    if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
    return res.json();
  }
  