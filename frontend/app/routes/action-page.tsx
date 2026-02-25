import type { Route } from "./+types/action-page";
import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router";
import {
  Button,
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Chip,
  AppBar,
  Toolbar,
} from "@mui/material";
import { AddCircle, List, CloudUpload, Refresh } from "@mui/icons-material";
import { fetchAdvisors } from "~/store/advisorsSlice";
import type { RootState, AppDispatch } from "~/store/store";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Agent Transfer Request" },
    { name: "description", content: "Manage agents and carrier transfers" },
  ];
}

export default function ActionPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { advisors, loading, error } = useSelector(
    (state: RootState) => state.advisors
  );

  useEffect(() => {
    dispatch(fetchAdvisors());
  }, [dispatch]);

  return (
    <>
      <AppBar position="static" elevation={0} sx={{ bgcolor: "#003366" }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 700, color: "#fff" }}>
            Agent Transfer Request
          </Typography>
          <Button color="inherit" component={Link} to="/create-and-transfer" startIcon={<AddCircle />}>
            Transfer agent
          </Button>
          <Button color="inherit" component={Link} to="/pending-transfers" startIcon={<List />}>
            Pending
          </Button>
          <Button color="inherit" component={Link} to="/carrier-formats" startIcon={<CloudUpload />}>
            Carrier formats
          </Button>
        </Toolbar>
      </AppBar>

      <main className="min-h-screen" style={{ backgroundColor: "#f5f5f5" }}>
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Box className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
              <Typography variant="h4" fontWeight="bold" color="text.primary">
                Dashboard
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Agents and transfer requests. Create an agent or start a new transfer request.
              </Typography>
            </div>
            <Box className="flex gap-2">
              <Button
                variant="outlined"
                startIcon={loading ? <CircularProgress size={18} /> : <Refresh />}
                onClick={() => dispatch(fetchAdvisors())}
                disabled={loading}
                sx={{ borderColor: "#003366", color: "#003366" }}
              >
                Refresh
              </Button>
            </Box>
          </Box>

          {error && (
            <Alert severity="error" className="mb-4">
              {error}
            </Alert>
          )}

          {/* Quick actions */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)", lg: "repeat(5, 1fr)" },
              gap: 2,
              mb: 4,
            }}
          >
            {/* <Card className="shadow-sm hover:shadow transition-shadow cursor-pointer" onClick={() => navigate("/advisors/new")}>
              <CardContent sx={{ textAlign: "center", py: 4 }}>
                <PersonAdd sx={{ fontSize: 48, color: "#003366", mb: 1 }} />
                <Typography variant="h6" fontWeight="600" color="text.primary">New agent</Typography>
                <Typography variant="body2" color="text.secondary">Add an agent with details or upload a document</Typography>
              </CardContent>
            </Card> */}
            <Card className="shadow-sm hover:shadow transition-shadow cursor-pointer" onClick={() => navigate("/create-and-transfer")}>
              <CardContent sx={{ textAlign: "center", py: 4 }}>
                <AddCircle sx={{ fontSize: 48, color: "#003366", mb: 1 }} />
                <Typography variant="h6" fontWeight="600" color="text.primary">New transfer request</Typography>
                <Typography variant="body2" color="text.secondary">Select agent and carriers to dispatch</Typography>
              </CardContent>
            </Card>
            <Card className="shadow-sm hover:shadow transition-shadow cursor-pointer" onClick={() => navigate("/pending-transfers")}>
              <CardContent sx={{ textAlign: "center", py: 4 }}>
                <List sx={{ fontSize: 48, color: "#003366", mb: 1 }} />
                <Typography variant="h6" fontWeight="600" color="text.primary">Pending transfers</Typography>
                <Typography variant="body2" color="text.secondary">View carrier submission status</Typography>
              </CardContent>
            </Card>
            <Card className="shadow-sm hover:shadow transition-shadow cursor-pointer" onClick={() => navigate("/carrier-formats")}>
              <CardContent sx={{ textAlign: "center", py: 4 }}>
                <CloudUpload sx={{ fontSize: 48, color: "#003366", mb: 1 }} />
                <Typography variant="h6" fontWeight="600" color="text.primary">Carrier formats</Typography>
                <Typography variant="body2" color="text.secondary">Configure request format per carrier</Typography>
              </CardContent>
            </Card>
            <Card className="shadow-sm hover:shadow transition-shadow cursor-pointer" onClick={() => navigate("/upload-document")}>
              <CardContent sx={{ textAlign: "center", py: 4 }}>
                <CloudUpload sx={{ fontSize: 48, color: "#003366", mb: 1 }} />
                <Typography variant="h6" fontWeight="600" color="text.primary">Upload Document</Typography>
                <Typography variant="body2" color="text.secondary">Extract data from PDF, Excel, or Image using AI</Typography>
              </CardContent>
            </Card>
          </Box>

          {/* Agents list */}
          <Card className="shadow-sm">
            <CardContent sx={{ pt: 3 }}>
              <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-2">
                Agents
              </Typography>
              <Typography variant="body2" color="text.secondary" className="mb-3">
                {advisors.length === 0
                  ? "No agents yet. Create a new agent to get started."
                  : "Registered agents. Use New transfer request to select an agent and dispatch to carriers."}
              </Typography>
              {loading ? (
                <Box className="flex justify-center py-6"><CircularProgress /></Box>
              ) : advisors.length === 0 ? (
                <Typography color="text.secondary">No agents.</Typography>
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
                    gap: 2,
                  }}
                >
                  {advisors.map((a) => (
                    <Card key={a.id} variant="outlined">
                      <CardContent>
                        <Typography fontWeight="600" color="text.primary">{a.name || a.npn || a.id}</Typography>
                        <Typography variant="body2" color="text.secondary">NPN {a.npn || "—"}</Typography>
                        <Chip label={a.status || "pending"} size="small" sx={{ mt: 1 }} variant="outlined" />
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Container>
      </main>
    </>
  );
}
