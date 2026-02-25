import { configureStore } from "@reduxjs/toolkit";
import agentTransferReducer from "./agentTransferSlice";
import carrierReducer from "./carrierSlice";
import pendingRequestsReducer from "./pendingRequestsSlice";

export const store = configureStore({
  reducer: {
    agentTransfer: agentTransferReducer,
    carriers: carrierReducer,
    pendingRequests: pendingRequestsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
