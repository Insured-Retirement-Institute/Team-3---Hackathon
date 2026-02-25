import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api, type ListCarrierSubmissionsResponse, type ListAdvisorsResponse } from "~/lib/api";
import { getCarrierDisplayName } from "./carrierSlice";
import { stateCodeToName } from "~/lib/states";

export interface PendingRequest {
  id: string;
  advisor_id: string;
  agent: string;
  carrier: string;
  state: string;
  date: string;
  status: string;
}

interface PendingRequestsState {
  requests: PendingRequest[];
  loading: boolean;
  error: string | null;
}

const initialState: PendingRequestsState = {
  requests: [],
  loading: false,
  error: null,
};

export const fetchPendingRequests = createAsyncThunk(
  "pendingRequests/fetchPendingRequests",
  async (_, { rejectWithValue }) => {
    try {
      const [subRes, advRes] = await Promise.all([
        api.get<ListCarrierSubmissionsResponse>("/api/admin/carrier-submissions"),
        api.get<ListAdvisorsResponse>("/api/admin/advisors"),
      ]);
      if (!subRes.success) throw new Error("Failed to load submissions");
      const list = subRes.data || [];
      const advisors = advRes.success && advRes.data ? advRes.data : [];
      const advisorNameById = new Map(
        advisors.map((a) => [a.id, (a.name || a.npn || a.id) || "—"])
      );
      const getAgentDisplayName = (advisorId: string) =>
        advisorNameById.get(advisorId) ?? advisorId;

      const requests: PendingRequest[] = list.map((s) => {
        const reqData = s.request_data || {};
        const submitted = reqData.submitted_states || [];
        const accepted = s.accepted_states || [];
        const rejected = s.rejected_states || [];
        const stateCodes = submitted.length ? submitted : accepted.length ? accepted : rejected;
        const stateDisplay = stateCodes.length
          ? stateCodes.map((c) => stateCodeToName(c)).join(", ")
          : "—";
        const carrierId = s.carrier_id || "";
        return {
          id: s.id,
          advisor_id: s.advisor_id,
          agent: getAgentDisplayName(s.advisor_id),
          carrier: getCarrierDisplayName(carrierId) || carrierId || "—",
          state: stateDisplay,
          date: s.created_at ? new Date(s.created_at).toLocaleDateString() : "—",
          status: s.status || "pending",
        };
      });
      return requests;
    } catch (e) {
      return rejectWithValue(
        e instanceof Error ? e.message : "Failed to fetch pending requests"
      );
    }
  }
);

const pendingRequestsSlice = createSlice({
  name: "pendingRequests",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchPendingRequests.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPendingRequests.fulfilled, (state, action) => {
        state.loading = false;
        state.requests = action.payload;
        state.error = null;
      })
      .addCase(fetchPendingRequests.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export default pendingRequestsSlice.reducer;
