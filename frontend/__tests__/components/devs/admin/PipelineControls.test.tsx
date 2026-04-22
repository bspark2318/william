import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PipelineControls from "@/components/devs/admin/PipelineControls";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => mockFetch.mockClear());

function ok(data: unknown) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  };
}

describe("PipelineControls", () => {
  it("renders both buttons", () => {
    render(<PipelineControls />);
    expect(
      screen.getByRole("button", { name: /run collect/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /run publish/i }),
    ).toBeInTheDocument();
  });

  it("fires POST /collect on click and shows response", async () => {
    mockFetch.mockResolvedValueOnce(
      ok({
        status: "ok",
        stories_added: 5,
        videos_added: 0,
        tweets_added: 12,
      }),
    );

    render(<PipelineControls />);
    const btn = screen.getByRole("button", { name: /run collect/i });
    await act(async () => {
      btn.click();
    });

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/admin-proxy/devs/collect",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(screen.getByText(/stories_added/)).toBeInTheDocument();
    expect(screen.getByText(/last collect response/i)).toBeInTheDocument();
  });

  it("fires POST /publish on click", async () => {
    mockFetch.mockResolvedValueOnce(
      ok({ status: "published", feed_size: 8, digest_title: "today" }),
    );

    render(<PipelineControls />);
    await act(async () => {
      screen.getByRole("button", { name: /run publish/i }).click();
    });

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/admin-proxy/devs/publish",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(screen.getByText(/feed_size/)).toBeInTheDocument();
  });

  it("disables both buttons while a request is in flight", async () => {
    let resolve!: (v: unknown) => void;
    mockFetch.mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      }),
    );

    render(<PipelineControls />);
    const collect = screen.getByRole("button", { name: /run collect/i });
    const publish = screen.getByRole("button", { name: /run publish/i });

    await act(async () => {
      collect.click();
    });

    expect(collect).toBeDisabled();
    expect(publish).toBeDisabled();

    await act(async () => {
      resolve(
        ok({
          status: "ok",
          stories_added: 0,
          videos_added: 0,
          tweets_added: 0,
        }),
      );
    });

    await waitFor(() => expect(collect).not.toBeDisabled());
  });

  it("shows an error banner when the request fails", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("x")),
      text: () => Promise.resolve("server blew up"),
    });

    render(<PipelineControls />);
    await act(async () => {
      screen.getByRole("button", { name: /run collect/i }).click();
    });

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/500/),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/server blew up/);
  });
});
