import type { Route } from "./+types/request";
import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router";
import {
  TextField,
  Button,
  Box,
  Container,
  Typography,
  MenuItem,
  Alert,
  CircularProgress,
  Select,
  InputLabel,
  FormControl,
  OutlinedInput,
  Chip,
  Checkbox,
  Card,
  CardContent,
} from "@mui/material";
import {
  submitAgentTransferForm,
  setFormData,
  resetForm,
} from "~/store/agentTransferSlice";
import { fetchAdvisors } from "~/store/advisorsSlice";
import { fetchPendingRequests } from "~/store/pendingRequestsSlice";
import { fetchCarriers } from "~/store/carrierSlice";
import type { RootState, AppDispatch } from "~/store/store";
import { US_STATE_CODES, stateCodeToName } from "~/lib/states";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "New Transfer Request" },
    { name: "description", content: "Submit a new agent transfer request" },
  ];
}

export default function Request() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { formData, loading, error, success, submissionIds } = useSelector(
    (state: RootState) => state.agentTransfer
  );
  const { advisors, loading: advisorsLoading } = useSelector(
    (state: RootState) => state.advisors
  );
  const { carriers } = useSelector((state: RootState) => state.carriers);
  const { requests: pendingRequests } = useSelector(
    (state: RootState) => state.pendingRequests
  );

  const inProgressStatuses = ["queued", "pending", "sent_to_carrier", "submitted"];
  const inProgressAdvisorIds = new Set(
    pendingRequests
      .filter((r) => inProgressStatuses.includes((r.status || "").toLowerCase()))
      .map((r) => r.advisor_id)
  );
  const availableAdvisors = advisors.filter((a) => !inProgressAdvisorIds.has(a.id));

  useEffect(() => {
    dispatch(fetchAdvisors());
    dispatch(fetchPendingRequests());
    dispatch(fetchCarriers());
  }, [dispatch]);

  const handleAdvisorChange = (e: { target: { value: string } }) => {
    dispatch(setFormData({ ...formData, advisor_id: e.target.value }));
  };

  const handleCarrierChange = (e: { target: { value: unknown } }) => {
    const value = e.target.value;
    dispatch(
      setFormData({
        ...formData,
        carriers: typeof value === "string" ? value.split(",") : (value as string[]),
      })
    );
  };

  const handleStatesChange = (e: { target: { value: unknown } }) => {
    const value = e.target.value;
    dispatch(
      setFormData({
        ...formData,
        states: typeof value === "string" ? value.split(",") : (value as string[]),
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await dispatch(
      submitAgentTransferForm({
        advisor_id: formData.advisor_id,
        carriers: formData.carriers,
        states: formData.states,
      })
    );
  };

  return (
    <main className="min-h-screen" style={{ backgroundColor: "#f5f5f5" }}>
      <Container maxWidth="lg" className="py-6">
        <Box className="mb-6">
          <Button variant="text" onClick={() => navigate("/")} sx={{ color: "#003366", mb: 2 }}>
            ← Back
          </Button>
          <Typography variant="h4" fontWeight="bold" color="text.primary">
            New Transfer Request
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Select an agent and carriers to dispatch
          </Typography>
        </Box>

        <Card className="mb-6 shadow-sm">
          <CardContent sx={{ pt: 3 }}>
            <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-4">
              Create transfer request
            </Typography>

            <Box component="form" onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <Alert severity="error" onClose={() => dispatch(resetForm())}>
                  {error}
                </Alert>
              )}

              {success && (
                <Alert severity="success" onClose={() => dispatch(resetForm())}>
                  Request submitted. Submission IDs: {submissionIds.join(", ")}.{" "}
                  <Link to="/pending-transfers" className="underline font-medium">
                    View pending transfers
                  </Link>
                </Alert>
              )}

              <FormControl fullWidth required disabled={advisorsLoading || loading} sx={{ mt: 2, mb: 2 }}>
                <InputLabel id="agent-label" shrink>Agent</InputLabel>
                <Select
                  labelId="agent-label"
                  value={formData.advisor_id}
                  onChange={handleAdvisorChange}
                  label="Agent"
                  displayEmpty
                  input={<OutlinedInput label="Agent" />}
                >
                  <MenuItem value="">Select agent</MenuItem>
                  {availableAdvisors.map((a) => (
                    <MenuItem key={a.id} value={a.id}>
                      {a.name || a.npn || a.id}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth disabled={loading} sx={{ mt: 2, mb: 2 }}>
                <InputLabel id="carriers-label" shrink>Carriers</InputLabel>
                <Select
                  labelId="carriers-label"
                  multiple
                  value={formData.carriers}
                  onChange={handleCarrierChange}
                  input={<OutlinedInput label="Carriers" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {(selected as string[]).map((id) => {
                        const c = carriers.find((x) => x.id === id);
                        return <Chip key={id} label={c ? c.name : id} size="small" />;
                      })}
                    </Box>
                  )}
                  MenuProps={{ PaperProps: { style: { maxHeight: 224 } } }}
                >
                  {carriers.map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      <Checkbox checked={formData.carriers.indexOf(c.id) > -1} />
                      {c.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth disabled={loading} sx={{ mt: 2, mb: 2 }}>
                <InputLabel id="states-label" shrink>States</InputLabel>
                <Select
                  labelId="states-label"
                  multiple
                  value={formData.states}
                  onChange={handleStatesChange}
                  input={<OutlinedInput label="States" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {(selected as string[]).map((code) => (
                        <Chip key={code} label={stateCodeToName(code)} size="small" />
                      ))}
                    </Box>
                  )}
                  MenuProps={{ PaperProps: { style: { maxHeight: 224 } } }}
                >
                  {US_STATE_CODES.map((code) => (
                    <MenuItem key={code} value={code}>
                      <Checkbox checked={formData.states.indexOf(code) > -1} />
                      {stateCodeToName(code)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Box className="flex justify-end gap-3 pt-2">
                <Button variant="outlined" onClick={() => navigate("/")} disabled={loading} sx={{ color: "#003366", borderColor: "#003366" }}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading || advisorsLoading || !formData.advisor_id}
                  sx={{ bgcolor: "#003366" }}
                >
                  {loading ? (
                    <>
                      <CircularProgress size={20} sx={{ mr: 1 }} color="inherit" />
                      Submitting...
                    </>
                  ) : (
                    "Submit request"
                  )}
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Container>
    </main>
  );
}
