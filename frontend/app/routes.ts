import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/action-page.tsx"),
  route("request", "routes/request.tsx"),
  route("pending-transfers", "routes/pending-transfers.tsx"),
] satisfies RouteConfig;
