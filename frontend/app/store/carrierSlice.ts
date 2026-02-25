import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";

export interface Carrier {
  id: string;
  name: string;
}

interface CarrierState {
  carriers: Carrier[];
  loading: boolean;
  error: string | null;
}

const initialState: CarrierState = {
  carriers: [],
  loading: false,
  error: null,
};

// Mock axios call that fetches carriers
export const fetchCarriers = createAsyncThunk(
  "carriers/fetchCarriers",
  async (_, { rejectWithValue }) => {
    try {
      // Simulate axios call with setTimeout
      const carriers = await new Promise<Carrier[]>((resolve) => {
        setTimeout(() => {
          resolve([
            { id: "1", name: "State Farm" },
            { id: "2", name: "Allstate" },
            { id: "3", name: "Progressive" },
            { id: "4", name: "Nationwide" },
            { id: "5", name: "American General" },
            { id: "6", name: "Jackson National" },
            { id: "7", name: "Equitable" },
            { id: "8", name: "Athene" },
            { id: "9", name: "Voya" },
            { id: "10", name: "Lincoln National" },
          ]);
        }, 500); // Simulate network delay
      });

      return carriers;
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : "Failed to fetch carriers"
      );
    }
  }
);

const carrierSlice = createSlice({
  name: "carriers",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchCarriers.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCarriers.fulfilled, (state, action) => {
        state.loading = false;
        state.carriers = action.payload;
        state.error = null;
      })
      .addCase(fetchCarriers.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export default carrierSlice.reducer;
