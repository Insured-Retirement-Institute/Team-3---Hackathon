import type { Route } from "./+types/create-and-transfer";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  Button,
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  TextField,
  Alert,
  CircularProgress,
  InputLabel,
  FormControl,
  OutlinedInput,
  Chip,
  Checkbox,
  ListItemText,
  MenuItem,
  Select,
} from "@mui/material";
import { api, type CreateAndTransferRequest, type CreateAndTransferResponse } from "~/lib/api";
import { fetchCarriers } from "~/store/carrierSlice";
import { US_STATE_CODES, stateCodeToName } from "~/lib/states";
import { emailError, phoneError } from "~/lib/validation";
import type { AppDispatch } from "~/store/store";
import { useDispatch, useSelector } from "react-redux";
import type { RootState } from "~/store/store";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Transfer Agent" },
    { name: "description", content: "Enter agent details and submit transfer requests to carriers" },
  ];
}

export default function CreateAndTransfer() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { carriers } = useSelector((state: RootState) => state.carriers);

  const [agent, setAgent] = useState({
    npn: "",
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    broker_dealer: "",
    license_states: [] as string[],
    status: "pending",
  });
  const [carriersSelected, setCarriersSelected] = useState<string[]>([]);
  const [statesSelected, setStatesSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState<{ advisor_id: string; submission_ids: string[] } | null>(null);

  useEffect(() => {
    dispatch(fetchCarriers());
  }, [dispatch]);

  const handleAgentChange = (e: { target: { name: string; value: unknown } }) => {
    const { name, value } = e.target;
    setAgent((prev) => ({ ...prev, [name]: value }));
  };

  const handleLicenseStatesChange = (e: { target: { value: unknown } }) => {
    const value = e.target.value;
    setAgent((prev) => ({
      ...prev,
      license_states: typeof value === "string" ? value.split(",") : (value as string[]),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(null);
    if (!agent.npn?.trim()) {
      setError("NPN is required.");
      return;
    }
    const eErr = emailError(agent.email ?? "");
    const pErr = phoneError(agent.phone ?? "");
    if (eErr || pErr) {
      setError(eErr || pErr);
      return;
    }
    if (!carriersSelected.length || !statesSelected.length) {
      setError("Select at least one carrier and one state.");
      return;
    }
    setLoading(true);
    try {
      const body: CreateAndTransferRequest = {
        agent: {
          npn: agent.npn.trim(),
          first_name: agent.first_name || undefined,
          last_name: agent.last_name || undefined,
          email: agent.email || undefined,
          phone: agent.phone || undefined,
          broker_dealer: agent.broker_dealer || undefined,
          license_states: agent.license_states?.length ? agent.license_states : undefined,
          status: "pending",
        },
        carriers: carriersSelected,
        states: statesSelected,
      };
      const res = await api.post<CreateAndTransferResponse>("/api/admin/create-and-transfer", body);
      setSuccess({ advisor_id: res.advisor_id, submission_ids: res.submission_ids || [] });
      setAgent({ npn: "", first_name: "", last_name: "", email: "", phone: "", broker_dealer: "", license_states: [], status: "pending" });
      setCarriersSelected([]);
      setStatesSelected([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transfer request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50">
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Box className="mb-6">
          <Button variant="text" onClick={() => navigate("/")} sx={{ color: "#003366", mb: 2 }}>
            ← Back
          </Button>
          <Typography variant="h4" fontWeight="bold" color="text.primary">
            Transfer agent
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Enter agent details, select carriers and states. One transfer request is created per carrier per state.
          </Typography>
        </Box>

        <Card className="shadow-sm">
          <CardContent sx={{ pt: 3 }}>
            <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-4">
              Agent details and transfer request
            </Typography>
            <Box component="form" onSubmit={handleSubmit}>
              {error && (
                <Alert severity="error" className="mb-4" onClose={() => setError("")}>
                  {error}
                </Alert>
              )}
              {success && (
                <Alert severity="success" className="mb-4">
                  Transfer requests submitted. Submission IDs: {success.submission_ids.length}.{" "}
                  <Button size="small" onClick={() => navigate("/pending-transfers")}>
                    View pending transfers
                  </Button>
                </Alert>
              )}

              <TextField
                required
                fullWidth
                name="npn"
                label="NPN"
                value={agent.npn}
                onChange={handleAgentChange}
                placeholder="National Producer Number"
              />
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2, mt: 2 }}>
                <TextField fullWidth name="first_name" label="First name" value={agent.first_name} onChange={handleAgentChange} />
                <TextField fullWidth name="last_name" label="Last name" value={agent.last_name} onChange={handleAgentChange} />
              </Box>
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2, mt: 2 }}>
                <TextField
                  fullWidth
                  name="email"
                  label="Email"
                  type="email"
                  value={agent.email}
                  onChange={handleAgentChange}
                  error={!!emailError(agent.email ?? "")}
                  helperText={emailError(agent.email ?? "")}
                />
                <TextField
                  fullWidth
                  name="phone"
                  label="Phone"
                  value={agent.phone}
                  onChange={handleAgentChange}
                  error={!!phoneError(agent.phone ?? "")}
                  helperText={phoneError(agent.phone ?? "")}
                />
              </Box>
              <TextField fullWidth name="broker_dealer" label="Broker dealer" value={agent.broker_dealer} onChange={handleAgentChange} sx={{ mt: 2 }} />
              <FormControl fullWidth sx={{ mt: 2 }}>
                <InputLabel>License states</InputLabel>
                <Select
                  multiple
                  value={agent.license_states || []}
                  onChange={handleLicenseStatesChange}
                  input={<OutlinedInput label="License states" />}
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
                      <Checkbox checked={(agent.license_states || []).indexOf(code) > -1} />
                      <ListItemText primary={stateCodeToName(code)} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth required sx={{ mt: 3, mb: 2 }}>
                <InputLabel id="carriers-label">Carriers to transfer</InputLabel>
                <Select
                  labelId="carriers-label"
                  multiple
                  value={carriersSelected}
                  onChange={(e) => setCarriersSelected(typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value)}
                  input={<OutlinedInput label="Carriers to transfer" />}
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
                      <Checkbox checked={carriersSelected.indexOf(c.id) > -1} />
                      {c.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth required sx={{ mb: 2 }}>
                <InputLabel id="states-label">States for transfer</InputLabel>
                <Select
                  labelId="states-label"
                  multiple
                  value={statesSelected}
                  onChange={(e) => setStatesSelected(typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value)}
                  input={<OutlinedInput label="States for transfer" />}
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
                      <Checkbox checked={statesSelected.indexOf(code) > -1} />
                      {stateCodeToName(code)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Box className="flex gap-3 mt-4">
                <Button type="submit" variant="contained" disabled={loading} sx={{ bgcolor: "#003366" }}>
                  {loading ? <CircularProgress size={24} color="inherit" /> : "Transfer agent"}
                </Button>
                <Button variant="outlined" onClick={() => navigate("/")}>
                  Cancel
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Container>
    </main>
  );
}
