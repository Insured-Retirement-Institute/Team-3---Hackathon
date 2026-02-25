import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api, type AdvisorListItem, type ListAdvisorsResponse, type SeedResponse } from "~/lib/api";

export interface AdvisorsState {
  advisors: AdvisorListItem[];
  loading: boolean;
  error: string | null;
  seedLoading: boolean;
  seedError: string | null;
}

const initialState: AdvisorsState = {
  advisors: [],
  loading: false,
  error: null,
  seedLoading: false,
  seedError: null,
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

export const seedAdvisors = createAsyncThunk(
  "advisors/seedAdvisors",
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.post<SeedResponse>("/api/admin/seed");
      if (!res.success) throw new Error("Seed failed");
      return res;
    } catch (e) {
      return rejectWithValue(e instanceof Error ? e.message : "Failed to seed advisors");
    }
  }
);

const advisorsSlice = createSlice({
  name: "advisors",
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
      state.seedError = null;
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
      })
      .addCase(seedAdvisors.pending, (state) => {
        state.seedLoading = true;
        state.seedError = null;
      })
      .addCase(seedAdvisors.fulfilled, (state, action) => {
        state.seedLoading = false;
        state.seedError = null;
        state.advisors = [...state.advisors]; // trigger refetch in UI or merge
      })
      .addCase(seedAdvisors.rejected, (state, action) => {
        state.seedLoading = false;
        state.seedError = action.payload as string;
      });
  },
});

export const { clearError: clearAdvisorsError } = advisorsSlice.actions;
export default advisorsSlice.reducer;
