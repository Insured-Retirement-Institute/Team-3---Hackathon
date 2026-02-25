import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";

export interface AgentTransferFormData {
  agent: string;
  carriers: string[];
  state: string;
}

interface AgentTransferState {
  formData: AgentTransferFormData;
  loading: boolean;
  error: string | null;
  success: boolean;
}

const initialState: AgentTransferState = {
  formData: {
    agent: "",
    carriers: [],
    state: "",
  },
  loading: false,
  error: null,
  success: false,
};

// Async thunk for submitting form data
export const submitAgentTransferForm = createAsyncThunk(
  "agentTransfer/submitForm",
  async (formData: AgentTransferFormData, { rejectWithValue }) => {
    try {
      // Simulate API call
      // In a real app, replace this with an actual API endpoint
      const response = await new Promise<AgentTransferFormData>((resolve) => {
        setTimeout(() => {
          resolve(formData);
        }, 1000);
      });

      return response;
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : "Failed to submit form"
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
        state.formData = action.payload;
        state.success = true;
        state.error = null;
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
