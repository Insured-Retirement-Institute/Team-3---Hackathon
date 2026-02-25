import { configureStore } from "@reduxjs/toolkit";
import agentTransferReducer from "./agentTransferSlice";
import carrierReducer from "./carrierSlice";
import pendingRequestsReducer from "./pendingRequestsSlice";
import advisorsReducer from "./advisorsSlice";

export const store = configureStore({
  reducer: {
    agentTransfer: agentTransferReducer,
    carriers: carrierReducer,
    pendingRequests: pendingRequestsReducer,
    advisors: advisorsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
