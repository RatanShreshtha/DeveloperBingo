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

/** The server has nothing at this address: the game or pool asked for does not exist. */
export class NotFoundError extends HttpError {
  constructor(response: Response = new Response(null, { status: 404 })) {
    super(response)
  }
}

/** The server is up but cannot reach a store it needs. Trying again shortly may work. */
export class UnavailableError extends HttpError {
  constructor(response: Response = new Response(null, { status: 503 })) {
    super(response)
  }
}

/** The failure for a response, typed by what it means so callers never read status codes. */
function failureFor(response: Response): HttpError {
  if (response.status === 404) return new NotFoundError(response)
  if (response.status === 503) return new UnavailableError(response)
  return new HttpError(response)
}

export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    throw failureFor(response)
  }
  return (await response.json()) as T
}
