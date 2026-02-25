import type { Route } from "./+types/newAdvisor";
import { useState } from "react";
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
import { CloudUpload } from "@mui/icons-material";
import { api, type CreateAdvisorRequest, type CreateAdvisorResponse } from "~/lib/api";
import { US_STATE_CODES, stateCodeToName } from "~/lib/states";
import { emailError, phoneError } from "~/lib/validation";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "New Agent" },
    { name: "description", content: "Create a new agent" },
  ];
}

export default function NewAdvisor() {
  const navigate = useNavigate();
  const [form, setForm] = useState<CreateAdvisorRequest>({
    npn: "",
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    broker_dealer: "",
    license_states: [],
    status: "pending",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (e: { target: { name: string; value: unknown } }) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleStatesChange = (e: { target: { value: unknown } }) => {
    const value = e.target.value;
    setForm((prev) => ({
      ...prev,
      license_states: typeof value === "string" ? value.split(",") : (value as string[]),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (!form.npn?.trim()) {
      setError("NPN is required.");
      return;
    }
    const eErr = emailError(form.email ?? "");
    const pErr = phoneError(form.phone ?? "");
    if (eErr || pErr) {
      setError(eErr || pErr);
      return;
    }
    setLoading(true);
    try {
      const res = await api.post<CreateAdvisorResponse>("/api/admin/advisors", {
        ...form,
        first_name: form.first_name || undefined,
        last_name: form.last_name || undefined,
        email: form.email || undefined,
        phone: form.phone || undefined,
        broker_dealer: form.broker_dealer || undefined,
        license_states: form.license_states?.length ? form.license_states : undefined,
      });
      setSuccess(`Agent created. ID: ${res.advisor_id}`);
      setForm({ npn: "", first_name: "", last_name: "", email: "", phone: "", broker_dealer: "", license_states: [], status: "pending" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create agent");
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
            New agent
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Enter agent details below or upload a document to extract details (when available).
          </Typography>
        </Box>

        {/* Manual entry */}
        <Card className="mb-6 shadow-sm">
          <CardContent sx={{ pt: 3 }}>
            <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-4">
              Enter details
            </Typography>
            <Box component="form" onSubmit={handleSubmit}>
              {error && (
                <Alert severity="error" className="mb-4" onClose={() => setError("")}>
                  {error}
                </Alert>
              )}
              {success && (
                <Alert severity="success" className="mb-4" onClose={() => setSuccess("")}>
                  {success}
                </Alert>
              )}
              <TextField
                required
                fullWidth
                name="npn"
                label="NPN"
                value={form.npn}
                onChange={handleChange}
                placeholder="National Producer Number"
              />
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2, mt: 2 }}>
                <TextField fullWidth name="first_name" label="First name" value={form.first_name} onChange={handleChange} />
                <TextField fullWidth name="last_name" label="Last name" value={form.last_name} onChange={handleChange} />
              </Box>
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2, mt: 2 }}>
                <TextField fullWidth name="email" label="Email" type="email" value={form.email} onChange={handleChange} error={!!emailError(form.email ?? "")} helperText={emailError(form.email ?? "")} />
                <TextField fullWidth name="phone" label="Phone" value={form.phone} onChange={handleChange} error={!!phoneError(form.phone ?? "")} helperText={phoneError(form.phone ?? "")} placeholder="e.g. (555) 123-4567" />
              </Box>
              <TextField fullWidth name="broker_dealer" label="Broker dealer" value={form.broker_dealer} onChange={handleChange} sx={{ mt: 2 }} />
              <FormControl fullWidth sx={{ mt: 2 }}>
                <InputLabel>License states</InputLabel>
                <Select
                  multiple
                  value={form.license_states || []}
                  onChange={handleStatesChange}
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
                      <Checkbox checked={(form.license_states || []).indexOf(code) > -1} />
                      <ListItemText primary={stateCodeToName(code)} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Box className="flex gap-3 mt-4">
                <Button type="submit" variant="contained" disabled={loading} sx={{ bgcolor: "#003366" }}>
                  {loading ? <CircularProgress size={24} color="inherit" /> : "Create agent"}
                </Button>
                <Button variant="outlined" onClick={() => navigate("/")}>
                  Cancel
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Upload placeholder - API in development */}
        <Card className="shadow-sm" sx={{ opacity: 0.9 }}>
          <CardContent sx={{ pt: 3 }}>
            <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-2">
              Upload document
            </Typography>
            <Typography variant="body2" color="text.secondary" className="mb-3">
              Upload an Excel or PDF file to extract agent details. This feature is currently in development.
            </Typography>
            <Button variant="outlined" startIcon={<CloudUpload />} disabled fullWidth sx={{ py: 2 }}>
              Upload Excel or PDF (coming soon)
            </Button>
          </CardContent>
        </Card>
      </Container>
    </main>
  );
}
