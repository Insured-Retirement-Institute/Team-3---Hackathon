import type { Route } from "./+types/pending-transfers";
import { useEffect, useState } from "react";
// Utility: isExpired (older than 2 days)
function isExpired(request: { date?: string }) {
  if (!request.date) return false;
  const reqDate = new Date(request.date);
  if (isNaN(reqDate.getTime())) return false;
  const now = new Date();
  const diffMs = now.getTime() - reqDate.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays > 2;
}

// Dynamic table component
function DynamicTransferTable({
  requests,
  highlightDateFn,
  handleViewPayload,
  label
}: {
  requests: any[],
  highlightDateFn?: (request: any) => boolean,
  handleViewPayload: (id: string) => void,
  label?: string
}) {
  if (!requests.length) {
    return <Typography color="text.secondary">No requests to display.</Typography>;
  }
  return (
    <Card sx={{ mb: 4 }}>
      <CardContent>
        {label && (
          <Typography variant="h6" className="font-bold mb-4" color={label === 'Needs Attention' ? 'error' : undefined}>
            {label}
          </Typography>
        )}
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow className="bg-gray-200">
                <TableCell className="font-semibold">Agent</TableCell>
                <TableCell className="font-semibold">Carrier</TableCell>
                <TableCell className="font-semibold">State</TableCell>
                <TableCell className="font-semibold">Date</TableCell>
                <TableCell className="font-semibold">Status</TableCell>
                <TableCell className="font-semibold">Payload</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {requests.map((request) => (
                <TableRow key={request.id} hover>
                  {/* <TableCell>{request.agent}</TableCell> */}
                  <TableCell>
                        {highlightDateFn && highlightDateFn(request) && (
                          <Schedule sx={{ color: '#FF9800', verticalAlign: 'middle', mr: 1 }} />
                        )}
                        {request.agent} 
                        </TableCell>
                  <TableCell>{getCarrierDisplayName(request.carrier)}</TableCell>
                  <TableCell>{request.state}</TableCell>
                  <TableCell>{request.date}</TableCell>
                  <TableCell>
                    <Chip
                      label={request.status}
                      color={getStatusColor(request.status) as "default" | "primary" | "success" | "error" | "info"}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Button size="small" startIcon={<Visibility />} onClick={() => handleViewPayload(request.id)}>
                      View payload
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
}
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router";
import {
  Container,
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import {
  HourglassTop,
  CheckCircle,
  Cancel,
  Schedule,
  Visibility,
} from "@mui/icons-material";
import { fetchPendingRequests } from "~/store/pendingRequestsSlice";
import { getCarrierDisplayName } from "~/store/carrierSlice";
import { api } from "~/lib/api";
import type { RootState, AppDispatch } from "~/store/store";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Pending Transfers" },
    { name: "description", content: "View pending agent transfer requests" },
  ];
}

const getStatusColor = (status: string) => {
  const s = (status || "").toLowerCase();
  if (s === "queued" || s === "pending") return "info";
  if (s === "sent_to_carrier" || s === "submitted") return "primary";
  if (s === "completed" || s === "approved") return "success";
  if (s === "error" || s === "rejected") return "error";
  return "default";
};

export default function PendingTransfers() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { requests: pendingRequests, loading, error } = useSelector(
    (state: RootState) => state.pendingRequests
  );
  const [payloadDialog, setPayloadDialog] = useState<{ open: boolean; payload: Record<string, unknown> | null; format_used?: string }>(
    {
      open: false,
      payload: null,
    }
  );
  const [payloadLoading, setPayloadLoading] = useState(false);
  // Filter state: only one status can be selected at a time
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);

  useEffect(() => {
    dispatch(fetchPendingRequests());
  }, [dispatch]);

  const handleViewPayload = async (submissionId: string) => {
    setPayloadLoading(true);
    setPayloadDialog({ open: true, payload: null });
    try {
      const res = await api.get<{ success: boolean; data: { request_data?: { payload?: Record<string, unknown>; carrier_format?: string } } }>(
        `/api/admin/carrier-submissions/${encodeURIComponent(submissionId)}`
      );
      const payload = res.success && res.data?.request_data?.payload ? res.data.request_data.payload : null;
      const raw = res.data?.request_data?.carrier_format;
      const format_used = raw === "carrier_a" ? "flat" : raw === "carrier_b" ? "nested" : raw ?? undefined;
      setPayloadDialog({ open: true, payload, format_used });
    } catch {
      setPayloadDialog({ open: true, payload: null });
    } finally {
      setPayloadLoading(false);
    }
  };

  // Expired = requests older than 2 days
  const expiredCount = pendingRequests.filter(isExpired).length;

  const statusCounts = {
    Expired: expiredCount,
    Sent: pendingRequests.filter((r) => ["sent_to_carrier", "submitted"].includes((r.status || "").toLowerCase())).length,
    Completed: pendingRequests.filter((r) => (r.status || "").toLowerCase() === "completed").length,
    Error: pendingRequests.filter((r) => (r.status || "").toLowerCase() === "error").length,
  };

  const statusCards = [
    {
      label: "Expired",
      count: statusCounts.Expired,
      icon: <Schedule sx={{ fontSize: 32, color: "#FF9800" }} />,
      bgColor: "#FFFBEA",
      filter: (_s: string, r: any) => isExpired(r),
    },
    {
      label: "Sent",
      count: statusCounts.Sent,
      icon: <HourglassTop sx={{ fontSize: 32, color: "#FDB913" }} />,
      bgColor: "#FFFBEA",
      filter: (s: string) => ["sent_to_carrier", "submitted"].includes(s),
    },
    {
      label: "Completed",
      count: statusCounts.Completed,
      icon: <CheckCircle sx={{ fontSize: 32, color: "#4CAF50" }} />,
      bgColor: "#F1F8F4",
      filter: (s: string) => s === "completed",
    },
    {
      label: "Error",
      count: statusCounts.Error,
      icon: <Cancel sx={{ fontSize: 32, color: "#F44336" }} />,
      bgColor: "#FFEBEE",
      filter: (s: string) => s === "error",
    },
  ];


  // Needs Attention: requests with status 'error' or older than 2 days
  const needsAttentionRequests = pendingRequests.filter((r) => {
    const status = (r.status || '').toLowerCase();
    return isExpired(r) || status === 'error';
  });

  // Filtered requests based on selected status
  const selectedCard = statusCards.find((c) => c.label === selectedStatus);
  const filteredRequests = selectedStatus && selectedCard
    ? pendingRequests.filter((r) => selectedCard.filter((r.status || '').toLowerCase(), r))
    : pendingRequests;

  const handleStatusCardClick = (label: string) => {
    setSelectedStatus((prev) => (prev === label ? null : label));
                  
                        
                        };

  return (
    <main className="min-h-screen bg-gray-50">
      <Container maxWidth="lg" className="py-6">
        <Box className="mb-8">
          <Button
            variant="text"
            onClick={() => navigate("/")}
            className="mb-4"
          >
            ← Back
          </Button>
          <Typography variant="h4" className="font-bold">
            Pending Transfers
          </Typography>
        </Box>

        {/* Status Cards */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, 1fr)",
              md: "repeat(4, 1fr)",
            },
            gap: 2,
            mb: 8,
          }}
        >
          {statusCards.map((card, index) => {
            const isSelected = selectedStatus === card.label;
            return (
              <Box key={index}>
                <Card
                  sx={{
                    backgroundColor: isSelected ? '#1976d2' : card.bgColor,
                    cursor: 'pointer',
                    boxShadow: isSelected ? 6 : undefined,
                    transition: 'background 0.2s',
                  }}
                  onClick={() => handleStatusCardClick(card.label)}
                  role="button"
                  tabIndex={0}
                  aria-pressed={isSelected}
                >
                  <CardContent className="flex flex-col items-center gap-2">
                    {card.icon}
                    <Typography variant="body2" className="text-gray-600" sx={{ color: isSelected ? '#fff' : undefined }}>
                      {card.label}
                    </Typography>
                    <Typography variant="h4" className="font-bold" sx={{ color: isSelected ? '#fff' : undefined }}>
                      {card.count}
                    </Typography>
                  </CardContent>
                </Card>
              </Box>
            );
          })}
        </Box>


        {/* Needs Attention Table */}
        {/* Dynamic Table Rendering */}
        {error && (
          <Alert severity="error" className="mb-4">
            {error}
          </Alert>
        )}
        {loading ? (
          <Box className="flex justify-center py-8">
            <CircularProgress />
          </Box>
        ) : selectedStatus && selectedCard ? (
          <DynamicTransferTable
            requests={filteredRequests}
            highlightDateFn={selectedStatus === 'Expired' ? isExpired : undefined}
            handleViewPayload={handleViewPayload}
            label={selectedStatus}
          />
        ) : (
          <DynamicTransferTable
            requests={pendingRequests}
            highlightDateFn={isExpired}
            handleViewPayload={handleViewPayload}
            label={undefined}
          />
        )}

        <Dialog open={payloadDialog.open} onClose={() => setPayloadDialog({ open: false, payload: null })} maxWidth="md" fullWidth>
          <DialogTitle>Payload sent to carrier</DialogTitle>
          <DialogContent>
            {payloadLoading ? (
              <Box className="flex justify-center py-4"><CircularProgress /></Box>
            ) : payloadDialog.payload ? (
              <Box>
                {payloadDialog.format_used && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Format: <strong>{payloadDialog.format_used}</strong>
                  </Typography>
                )}
                <Box component="pre" sx={{ p: 2, bgcolor: "#1a1a1a", color: "#e0e0e0", borderRadius: 1, overflow: "auto", fontSize: "0.75rem", fontFamily: "monospace" }}>
                  <code>{JSON.stringify(payloadDialog.payload, null, 2)}</code>
                </Box>
              </Box>
            ) : (
              <Typography color="text.secondary">No payload data for this submission.</Typography>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPayloadDialog({ open: false, payload: null })}>Close</Button>
          </DialogActions>
        </Dialog>
      </Container>
    </main>
  );
}
