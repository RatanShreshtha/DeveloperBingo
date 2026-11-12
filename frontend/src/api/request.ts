export class HttpError extends Error {
  readonly response: Response
  readonly status: number

  constructor(response: Response) {
    super(`Request failed with status ${response.status}`)
    this.name = 'HttpError'
    this.response = response
    this.status = response.status
  }
}

export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    throw new HttpError(response)
  }
  return (await response.json()) as T
}
