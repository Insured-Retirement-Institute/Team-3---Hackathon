import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api, type AdvisorListItem, type ListAdvisorsResponse } from "~/lib/api";

export interface AdvisorsState {
  advisors: AdvisorListItem[];
  loading: boolean;
  error: string | null;
}

const initialState: AdvisorsState = {
  advisors: [],
  loading: false,
  error: null,
};

export const fetchAdvisors = createAsyncThunk(
  "advisors/fetchAdvisors",
  async (status: string | undefined, { rejectWithValue }) => {
    try {
      const params = status ? { status } : undefined;
      const res = await api.get<ListAdvisorsResponse>("/api/admin/advisors", params);
      if (!res.success) throw new Error("Failed to load advisors");
      return res.data;
    } catch (e) {
      return rejectWithValue(e instanceof Error ? e.message : "Failed to fetch advisors");
    }
  }
);

const advisorsSlice = createSlice({
  name: "advisors",
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAdvisors.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAdvisors.fulfilled, (state, action) => {
        state.loading = false;
        state.advisors = action.payload;
        state.error = null;
      })
      .addCase(fetchAdvisors.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearError: clearAdvisorsError } = advisorsSlice.actions;
export default advisorsSlice.reducer;
