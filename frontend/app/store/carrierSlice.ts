import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api, type CarriersListResponse } from "~/lib/api";

export interface Carrier {
  id: string;
  name: string;
  default_template?: string;
  has_custom_yaml?: boolean;
}

// Match backend carrier_registry.py CARRIER_NAMES so display names are correct even before API load
const FALLBACK_CARRIERS: Carrier[] = [
  { id: "1", name: "MassMutual" },
  { id: "2", name: "Nationwide" },
  { id: "3", name: "Principal" },
  { id: "4", name: "Lincoln Financial" },
  { id: "5", name: "Pacific Life" },
  { id: "6", name: "Guardian Life" },
  { id: "7", name: "Ameritas" },
  { id: "8", name: "Transamerica" },
];

const LEGACY_CARRIER_NAMES: Record<string, string> = {
  "carrier-a": "MassMutual",
  "carrier-b": "Nationwide",
  "carrier-c": "Principal",
  "carrier-d": "Lincoln Financial",
  "carrier-e": "Pacific Life",
  "carrier-f": "Guardian Life",
  "carrier-g": "Ameritas",
  "carrier-h": "Transamerica",
};

export function getCarrierDisplayName(carrierId: string, carriers?: Carrier[]): string {
  const list = carriers && carriers.length > 0 ? carriers : FALLBACK_CARRIERS;
  const c = list.find((x) => x.id === carrierId);
  if (c) return c.name;
  return LEGACY_CARRIER_NAMES[carrierId] ?? carrierId;
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

export const fetchCarriers = createAsyncThunk(
  "carriers/fetchCarriers",
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.get<CarriersListResponse>("/api/admin/carriers");
      if (!res.success) throw new Error("Failed to load carriers");
      return res.data || [];
    } catch (e) {
      return rejectWithValue(e instanceof Error ? e.message : "Failed to fetch carriers");
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
        state.carriers = action.payload.length ? action.payload : FALLBACK_CARRIERS;
        state.error = null;
      })
      .addCase(fetchCarriers.rejected, (state, action) => {
        state.loading = false;
        state.carriers = FALLBACK_CARRIERS;
        state.error = action.payload as string;
      });
  },
});

export default carrierSlice.reducer;
