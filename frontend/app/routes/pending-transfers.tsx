import type { Route } from "./+types/pending-transfers";
import { useEffect } from "react";
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
} from "@mui/material";
import {
  HourglassTop,
  CheckCircle,
  Cancel,
  Schedule,
} from "@mui/icons-material";
import { fetchPendingRequests } from "~/store/pendingRequestsSlice";
import type { RootState, AppDispatch } from "~/store/store";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Pending Transfers" },
    { name: "description", content: "View pending agent transfer requests" },
  ];
}

const getStatusColor = (status: string) => {
  switch (status) {
    case "Pending":
      return "primary";
    case "In Progress":
      return "warning";
    case "Approved":
      return "success";
    case "Rejected":
      return "error";
    default:
      return "default";
  }
};

export default function PendingTransfers() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { requests: pendingRequests, loading, error } = useSelector(
    (state: RootState) => state.pendingRequests
  );

  useEffect(() => {
    dispatch(fetchPendingRequests());
  }, [dispatch]);

  // Calculate status counts from pending requests
  const statusCounts = {
    "In Progress": pendingRequests.filter((r) => r.status === "In Progress").length,
    Approved: pendingRequests.filter((r) => r.status === "Approved").length,
    Rejected: pendingRequests.filter((r) => r.status === "Rejected").length,
    Pending: pendingRequests.filter((r) => r.status === "Pending").length,
  };

  const statusCards = [
    {
      label: "In Progress",
      count: statusCounts["In Progress"],
      icon: <HourglassTop sx={{ fontSize: 32, color: "#FDB913" }} />,
      bgColor: "#FFFBEA",
    },
    {
      label: "Approved",
      count: statusCounts.Approved,
      icon: <CheckCircle sx={{ fontSize: 32, color: "#4CAF50" }} />,
      bgColor: "#F1F8F4",
    },
    {
      label: "Rejected",
      count: statusCounts.Rejected,
      icon: <Cancel sx={{ fontSize: 32, color: "#F44336" }} />,
      bgColor: "#FFEBEE",
    },
    {
      label: "Pending",
      count: statusCounts.Pending,
      icon: <Schedule sx={{ fontSize: 32, color: "#2196F3" }} />,
      bgColor: "#E3F2FD",
    },
  ];

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
          {statusCards.map((card, index) => (
            <Box key={index}>
              <Card sx={{ backgroundColor: card.bgColor }}>
                <CardContent className="flex flex-col items-center gap-2">
                  {card.icon}
                  <Typography variant="body2" className="text-gray-600">
                    {card.label}
                  </Typography>
                  <Typography variant="h4" className="font-bold">
                    {card.count}
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          ))}
        </Box>

        {/* Transfers Table */}
        <Card>
          <CardContent>
            <Typography variant="h6" className="font-bold mb-4">
              Transfer Requests
            </Typography>

            {error && (
              <Alert severity="error" className="mb-4">
                {error}
              </Alert>
            )}

            {loading ? (
              <Box className="flex justify-center py-8">
                <CircularProgress />
              </Box>
            ) : (
              <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow className="bg-gray-200">
                    <TableCell className="font-semibold">Agent</TableCell>
                    <TableCell className="font-semibold">Carrier</TableCell>
                    <TableCell className="font-semibold">State</TableCell>
                    <TableCell className="font-semibold">Date Requested</TableCell>
                    <TableCell className="font-semibold">Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pendingRequests.map((request) => (
                    <TableRow key={request.id} hover>
                      <TableCell>{request.agent}</TableCell>
                      <TableCell>{request.carrier}</TableCell>
                      <TableCell>{request.state}</TableCell>
                      <TableCell>{request.date}</TableCell>
                      <TableCell>
                        <Chip
                          label={request.status}
                          color={getStatusColor(request.status) as any}
                          variant="outlined"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            )}
          </CardContent>
        </Card>
      </Container>
    </main>
  );
}
