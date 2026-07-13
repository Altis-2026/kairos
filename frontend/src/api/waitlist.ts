import { apiFetch } from "./client";

export interface WaitlistResponse {
  joined: boolean;
  already: boolean;
  count: number;
}

export function joinWaitlist(
  email: string,
  useCase = "",
  product = "janus"
): Promise<WaitlistResponse> {
  return apiFetch<WaitlistResponse>("/waitlist", {
    method: "POST",
    body: JSON.stringify({ email, product, use_case: useCase }),
  });
}
