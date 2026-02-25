import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "~/lib/api";

export interface AgentTransferFormData {
  advisor_id: string;
  carriers: string[];
  states: string[];
}

interface AgentTransferState {
  formData: AgentTransferFormData;
  loading: boolean;
  error: string | null;
  success: boolean;
  submissionIds: string[];
}

const initialState: AgentTransferState = {
  formData: {
    advisor_id: "",
    carriers: [],
    states: [],
  },
  loading: false,
  error: null,
  success: false,
  submissionIds: [],
};

export const submitAgentTransferForm = createAsyncThunk(
  "agentTransfer/submitForm",
  async (
    { advisor_id, carriers, states }: AgentTransferFormData,
    { rejectWithValue }
  ) => {
    try {
      if (!advisor_id) throw new Error("Select an advisor");
      const carrierFormat = (c: string) =>
        c === "2" ? "nested" : "flat";
      const body = {
        carriers: (carriers.length ? carriers : ["1", "2"]).map(
          (carrier_id) => ({
            carrier_id,
            carrier_format: carrierFormat(carrier_id),
            integration_method: "api",
            submitted_states: states.length ? states : ["CA", "TX"],
          })
        ),
      };
      const res = await api.post<{
        success: boolean;
        submission_ids: string[];
        status: string;
      }>(`/api/admin/advisors/${advisor_id}/carriers/dispatch-all`, body);
      if (!res.success) throw new Error("Dispatch failed");
      return { submissionIds: (res as { submission_ids?: string[] }).submission_ids || [] };
    } catch (e) {
      return rejectWithValue(
        e instanceof Error ? e.message : "Failed to submit request"
      );
    }
  }
);

const agentTransferSlice = createSlice({
  name: "agentTransfer",
  initialState,
  reducers: {
    setFormData: (state, action) => {
      state.formData = action.payload;
    },
    resetForm: (state) => {
      state.formData = initialState.formData;
      state.error = null;
      state.success = false;
      state.submissionIds = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitAgentTransferForm.pending, (state) => {
        state.loading = true;
        state.error = null;
        state.success = false;
      })
      .addCase(submitAgentTransferForm.fulfilled, (state, action) => {
        state.loading = false;
        state.success = true;
        state.error = null;
        state.submissionIds = action.payload.submissionIds || [];
      })
      .addCase(submitAgentTransferForm.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
        state.success = false;
      });
  },
});

export const { setFormData, resetForm } = agentTransferSlice.actions;
export default agentTransferSlice.reducer;
