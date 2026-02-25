import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";

export interface PendingRequest {
  id: number;
  agent: string;
  carrier: string;
  state: string;
  date: string;
  status: "Pending" | "In Progress" | "Approved" | "Rejected";
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

// Mock data
const mockPendingRequests: PendingRequest[] = [
  {
    id: 1,
    agent: "John Smith",
    carrier: "State Farm",
    state: "CA",
    date: "2024-02-20",
    status: "Pending",
  },
  {
    id: 2,
    agent: "Jane Doe",
    carrier: "Allstate",
    state: "TX",
    date: "2024-02-21",
    status: "In Progress",
  },
  {
    id: 3,
    agent: "Mike Johnson",
    carrier: "Progressive",
    state: "NY",
    date: "2024-02-22",
    status: "Approved",
  },
    {
    id: 4,
    agent: "Jessica Day",
    carrier: "Progressive",
    state: "CA",
    date: "2024-02-22",
    status: "Approved",
  },
];

// Async thunk for fetching pending requests
export const fetchPendingRequests = createAsyncThunk(
  "pendingRequests/fetchPendingRequests",
  async (_, { rejectWithValue }) => {
    try {
      // Simulate axios call with setTimeout
      const requests = await new Promise<PendingRequest[]>((resolve) => {
        setTimeout(() => {
          resolve(mockPendingRequests);
        }, 200); // Simulate network delay
      });

      return requests;
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : "Failed to fetch pending requests"
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
