import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/action-page.tsx"),
  route("advisors/new", "routes/newAdvisor.tsx"),
  route("request", "routes/request.tsx"),
  route("pending-transfers", "routes/pending-transfers.tsx"),
  route("carrier-formats", "routes/carrierFormats.tsx"),
  route("upload-document", "routes/upload-document.tsx"),
] satisfies RouteConfig;
