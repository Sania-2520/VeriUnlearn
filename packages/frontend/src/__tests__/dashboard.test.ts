import { loadLiveDashboard } from "@/lib/api/dashboard"
import * as client from "@/lib/api/client"
import * as unlearning from "@/lib/api/unlearning"
import * as admin from "@/lib/api/admin"

jest.mock("@/lib/api/client", () => ({
  getSystemHealth: jest.fn(),
  getRegistryStats: jest.fn(),
}))
jest.mock("@/lib/api/unlearning", () => ({
  listRequests: jest.fn(),
}))
jest.mock("@/lib/api/admin", () => ({
  listJobs: jest.fn(),
}))

const mockedClient = client as jest.Mocked<typeof client>
const mockedUnlearning = unlearning as jest.Mocked<typeof unlearning>
const mockedAdmin = admin as jest.Mocked<typeof admin>

describe("loadLiveDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("falls back to sample data when all API calls fail", async () => {
    mockedClient.getSystemHealth.mockRejectedValue(new Error("down"))
    mockedClient.getRegistryStats.mockRejectedValue(new Error("down"))
    mockedAdmin.listJobs.mockRejectedValue(new Error("down"))
    mockedUnlearning.listRequests.mockRejectedValue(new Error("down"))

    const snap = await loadLiveDashboard()
    expect(snap.sources).toBe("fallback")
    expect(snap.activeJobs).toBeNull()
    expect(snap.backendHealthy).toBeNull()
  })

  it("maps live health and request data when APIs respond", async () => {
    mockedClient.getSystemHealth.mockResolvedValue({ backend: "healthy" })
    mockedClient.getRegistryStats.mockResolvedValue({})
    mockedAdmin.listJobs.mockResolvedValue({
      data: [
        { status: "running" },
        { status: "running" },
        { status: "completed" },
      ],
      meta: { page: 1, page_size: 100, total: 3 },
    })
    mockedUnlearning.listRequests.mockResolvedValue({
      data: [
        { status: "pending" },
        { status: "completed" },
        { status: "success" },
      ],
      meta: { page: 1, page_size: 100, total: 3 },
    })

    const snap = await loadLiveDashboard()
    expect(snap.sources).toBe("live")
    expect(snap.backendHealthy).toBe(true)
    expect(snap.activeJobs).toBe(2)
    expect(snap.modelCount).toBe(3)
    expect(snap.runningUnlearningRequests).toBe(1)
    expect(snap.completedUnlearningRequests).toBe(2)
  })

  it("marks backend unhealthy when health reports non-healthy", async () => {
    mockedClient.getSystemHealth.mockResolvedValue({ backend: "unavailable" })
    mockedClient.getRegistryStats.mockResolvedValue({})
    mockedAdmin.listJobs.mockResolvedValue({ data: [], meta: { page: 1, page_size: 100, total: 0 } })
    mockedUnlearning.listRequests.mockResolvedValue({ data: [], meta: { page: 1, page_size: 100, total: 0 } })

    const snap = await loadLiveDashboard()
    expect(snap.sources).toBe("live")
    expect(snap.backendHealthy).toBe(false)
  })
})