import type { Route } from "./+types/carrierFormats";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import {
  Button,
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { CloudUpload } from "@mui/icons-material";
import {
  api,
  type CarrierFormatIdsResponse,
  type CarriersListResponse,
  type SampleFormatResponse,
  type TestTransformResponse,
  type ListAdvisorsResponse,
} from "~/lib/api";

const FALLBACK_SAMPLE_YAML = `# Standard carrier template (flat)
# Reference shape. Upload carrier-specific YAMLs for different formats.

request:
  carrierId: string
  advisor:
    advisor_id: string
    npn: string
    first_name: string
    last_name: string
    email: string
    phone: string
    broker_dealer: string
    license_states: list of strings
  statesRequested: list of state codes
`;

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Carrier format YAML" },
    { name: "description", content: "Upload YAML that defines carrier request/response format" },
  ];
}

export default function CarrierFormats() {
  const navigate = useNavigate();
  const [carrierId, setCarrierId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState("");
  const [carriers, setCarriers] = useState<{ carrier_id: string; name: string; template_used?: string; default_template?: string }[]>([]);
  const [carrierOptions, setCarrierOptions] = useState<{ id: string; name: string }[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [sampleYaml, setSampleYaml] = useState("");
  const [sampleTemplateName, setSampleTemplateName] = useState("");
  const [loadingSample, setLoadingSample] = useState(false);
  const [advisors, setAdvisors] = useState<{ id: string; name: string }[]>([]);
  const [testCarrierId, setTestCarrierId] = useState("");
  const [testAdvisorId, setTestAdvisorId] = useState("");
  const [testStates, setTestStates] = useState<string[]>([]);
  const [testResult, setTestResult] = useState<{
    payload: Record<string, unknown>;
    format_used: string;
    message?: string | null;
    custom_yaml_uploaded?: boolean;
    bedrock_used?: boolean;
  } | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState("");

  const loadCarriers = async () => {
    try {
      const res = await api.get<CarriersListResponse>("/api/admin/carriers");
      setCarrierOptions(res.success && res.data ? res.data : []);
    } catch {
      setCarrierOptions([]);
    }
  };

  const loadList = async () => {
    setLoadingList(true);
    try {
      const res = await api.get<CarrierFormatIdsResponse>("/api/admin/carrier-formats");
      setCarriers(res.success && res.carriers ? res.carriers : []);
    } catch {
      setCarriers([]);
    } finally {
      setLoadingList(false);
    }
  };

  const loadSample = async () => {
    setLoadingSample(true);
    try {
      const res = await api.get<SampleFormatResponse>("/api/admin/carrier-formats/sample");
      setSampleYaml(res.success && res.yaml ? res.yaml : FALLBACK_SAMPLE_YAML);
      setSampleTemplateName(res.template_name || "standard (flat)");
    } catch {
      setSampleYaml(FALLBACK_SAMPLE_YAML);
      setSampleTemplateName("standard (flat)");
    } finally {
      setLoadingSample(false);
    }
  };

  const loadAdvisors = async () => {
    try {
      const res = await api.get<ListAdvisorsResponse>("/api/admin/advisors");
      setAdvisors(res.success && res.data ? res.data.map((a) => ({ id: a.id, name: a.name || a.npn || a.id })) : []);
    } catch {
      setAdvisors([]);
    }
  };

  useEffect(() => {
    loadCarriers();
    loadList();
    loadSample();
    loadAdvisors();
  }, []);

  const runTestTransform = async () => {
    setTestError("");
    setTestResult(null);
    if (!testAdvisorId || !testCarrierId) {
      setTestError("Select carrier and agent.");
      return;
    }
    setTestLoading(true);
    try {
      const res = await api.post<TestTransformResponse>("/api/admin/carrier-formats/test-transform", {
        carrier_id: testCarrierId,
        advisor_id: testAdvisorId,
        states: testStates,
      });
      if (res.success)
        setTestResult({
          payload: res.payload,
          format_used: res.format_used,
          message: res.message ?? undefined,
          custom_yaml_uploaded: res.custom_yaml_uploaded,
          bedrock_used: res.bedrock_used,
        });
      else setTestError("Transform failed.");
    } catch (err) {
      setTestError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setTestLoading(false);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadError("");
    setUploadSuccess("");
    const id = carrierId.trim();
    if (!id) {
      setUploadError("Select a carrier");
      return;
    }
    if (!file) {
      setUploadError("Select a YAML file");
      return;
    }
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await api.postForm<{ success: boolean; saved_as: string }>(
        `/api/admin/carrier-formats/${encodeURIComponent(id)}`,
        form
      );
      const name = carrierOptions.find((c) => c.id === id)?.name || id;
      setUploadSuccess(`Saved format for ${name}.`);
      setCarrierId("");
      setFile(null);
      loadList();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <main className="min-h-screen" style={{ backgroundColor: "#f5f5f5" }}>
      <Container maxWidth="md" className="py-6">
        <Box className="mb-6">
          <Button variant="text" onClick={() => navigate("/")} sx={{ color: "#003366", mb: 2 }}>
            ← Back
          </Button>
          <Typography variant="h4" fontWeight="bold" color="text.primary">
            Carrier format YAML
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Upload a YAML file that describes the carrier API request format. It will be used to transform agent data before sending to each carrier.
          </Typography>
        </Box>

        <Card className="mb-6 shadow-sm">
          <CardContent sx={{ pt: 3 }}>
            <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-4">
              Upload format
            </Typography>
            <Box component="form" onSubmit={handleUpload}>
              {uploadError && (
                <Alert severity="error" className="mb-4" onClose={() => setUploadError("")}>
                  {uploadError}
                </Alert>
              )}
              {uploadSuccess && (
                <Alert severity="success" className="mb-4" onClose={() => setUploadSuccess("")}>
                  {uploadSuccess}
                </Alert>
              )}
              <FormControl fullWidth required sx={{ mt: 2, mb: 2 }}>
                <InputLabel id="carrier-select-label" shrink>Carrier</InputLabel>
                <Select
                  labelId="carrier-select-label"
                  value={carrierId}
                  onChange={(e) => setCarrierId(e.target.value)}
                  label="Carrier"
                  displayEmpty
                  inputProps={{ "aria-label": "Carrier" }}
                >
                  <MenuItem value="">Select carrier</MenuItem>
                  {carrierOptions.map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Box className="mt-4 mb-4">
                <Button
                  variant="outlined"
                  component="label"
                  startIcon={<CloudUpload />}
                  fullWidth
                  sx={{ py: 2, borderColor: "#003366", color: "#003366" }}
                >
                  {file ? file.name : "Choose YAML file"}
                  <input
                    type="file"
                    accept=".yaml,.yml"
                    hidden
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </Button>
              </Box>
              <Button
                type="submit"
                variant="contained"
                disabled={uploading || !carrierId.trim() || !file}
                sx={{ bgcolor: "#003366" }}
              >
                {uploading ? <CircularProgress size={24} color="inherit" /> : "Upload"}
              </Button>
            </Box>
          </CardContent>
        </Card>

        <Card className="mb-6 shadow-sm">
          <CardContent sx={{ pt: 3 }}>
            <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-2">
              Known Carrier Formats
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Will update this to pull from data source 
          </Typography>
            {loadingList ? (
              <Box className="flex justify-center py-4"><CircularProgress /></Box>
            ) : carriers.length === 0 ? (
              <Typography color="text.secondary">None yet. Upload a YAML above.</Typography>
            ) : (
              <Box sx={{ overflowX: "auto" }}>
                <Box
                  component="table"
                  sx={{
                    width: "100%",
                    borderCollapse: "collapse",
                    fontSize: "0.875rem",
                  }}
                >
                  <Box component="thead">
                    <Box component="tr" sx={{ borderBottom: "2px solid #ddd", backgroundColor: "#fafafa" }}>
                      <Box component="th" sx={{ padding: "12px", textAlign: "left", fontWeight: "600" }}>
                        Carrier Name
                      </Box>
                      <Box component="th" sx={{ padding: "12px", textAlign: "left", fontWeight: "600" }}>
                        Carrier ID
                      </Box>
                      <Box component="th" sx={{ padding: "12px", textAlign: "left", fontWeight: "600" }}>
                        Template
                      </Box>
                      <Box component="th" sx={{ padding: "12px", textAlign: "left", fontWeight: "600" }}>
                        Default Template
                      </Box>
                    </Box>
                  </Box>
                  <Box component="tbody">
                    {carriers.map((c) => (
                      <Box
                        component="tr"
                        key={c.carrier_id}
                        sx={{
                          borderBottom: "1px solid #eee",
                          "&:hover": { backgroundColor: "#f9f9f9" },
                        }}
                      >
                        <Box component="td" sx={{ padding: "12px" }}>
                          {c.name}
                        </Box>
                        <Box component="td" sx={{ padding: "12px", fontFamily: "monospace", fontSize: "0.8rem" }}>
                          {c.carrier_id}
                        </Box>
                        <Box component="td" sx={{ padding: "12px" }}>
                          {c.template_used ?? "custom_yaml"}
                        </Box>
                        <Box component="td" sx={{ padding: "12px" }}>
                          {c.default_template || "—"}
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>

        <Card className="mb-6 shadow-sm">
          <CardContent sx={{ pt: 3 }}>
            <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-2">
              Test transform (no submit)
            </Typography>
            <Typography variant="body2" color="text.secondary" className="mb-2">
              See the exact JSON that would be sent to a carrier. Run this to compare standard vs custom YAML without waiting for async dispatch.
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, alignItems: "center", mb: 2 }}>
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel>Carrier</InputLabel>
                <Select value={testCarrierId} onChange={(e) => setTestCarrierId(e.target.value)} label="Carrier">
                  <MenuItem value="">Select</MenuItem>
                  {carrierOptions.map((c) => (
                    <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Agent</InputLabel>
                <Select value={testAdvisorId} onChange={(e) => setTestAdvisorId(e.target.value)} label="Agent">
                  <MenuItem value="">Select</MenuItem>
                  {advisors.map((a) => (
                    <MenuItem key={a.id} value={a.id}>{a.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button variant="contained" onClick={runTestTransform} disabled={testLoading || !testCarrierId || !testAdvisorId} sx={{ bgcolor: "#003366" }}>
                {testLoading ? <CircularProgress size={24} color="inherit" /> : "Run test"}
              </Button>
            </Box>
            {testError && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setTestError("")}>{testError}</Alert>}
            {testResult && (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Format used: <strong>{testResult.format_used}</strong>
                  {testResult.bedrock_used === true && " (Bedrock)"}
                </Typography>
                {testResult.message && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    {testResult.message}
                  </Alert>
                )}
                <Box component="pre" sx={{ p: 2, bgcolor: "#1a1a1a", color: "#e0e0e0", borderRadius: 1, overflow: "auto", fontSize: "0.75rem", fontFamily: "monospace" }}>
                  <code>{JSON.stringify(testResult.payload, null, 2)}</code>
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardContent sx={{ pt: 3 }}>
            <Typography variant="h6" fontWeight="600" color="text.primary" className="mb-2">
              Standard carrier template {sampleTemplateName ? `(${sampleTemplateName})` : "(flat)"}
            </Typography>
            <Typography variant="body2" color="text.secondary" className="mb-2">
              Reference shape. Upload carrier-specific YAMLs for different formats.
            </Typography>
            {loadingSample ? (
              <Box className="flex justify-center py-4"><CircularProgress /></Box>
            ) : sampleYaml ? (
              <Box
                component="pre"
                sx={{
                  p: 2,
                  bgcolor: "#1a1a1a",
                  color: "#e0e0e0",
                  borderRadius: 1,
                  overflow: "auto",
                  fontSize: "0.8rem",
                  fontFamily: "monospace",
                }}
              >
                <code>{sampleYaml}</code>
              </Box>
            ) : (
              <Typography color="text.secondary">Could not load sample.</Typography>
            )}
          </CardContent>
        </Card>
      </Container>
    </main>
  );
}
