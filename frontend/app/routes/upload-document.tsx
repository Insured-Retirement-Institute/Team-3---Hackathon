import type { Route } from "./+types/upload-document";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import {
  Container,
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Paper,
  Chip,
  TextField,
  IconButton,
  Tooltip,
  AppBar,
  Toolbar,
} from "@mui/material";
import {
  CloudUpload,
  Description,
  CheckCircle,
  Edit,
  Save,
  Cancel,
  Check,
  AddCircle,
  List,
  PersonAdd,
} from "@mui/icons-material";
import { api } from "~/lib/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Upload Document" },
    { name: "description", content: "Upload PDF, Excel, or Image to extract data" },
  ];
}

interface ExtractedData {
  success: boolean;
  filename: string;
  data: {
    form_fields: Record<string, string>;
    highlighted_items: string[];
    background_info: Record<string, string>;
    signatures: Record<string, string>;
  };
  confidence: number;
  pages_analyzed: number;
  notes: string;
}

export default function UploadDocument() {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [transferring, setTransferring] = useState(false);
  const [transferSuccess, setTransferSuccess] = useState<string | null>(null);
  
  // Track edited fields
  const [editedFields, setEditedFields] = useState<Record<string, string>>({});
  const [approvedFields, setApprovedFields] = useState<Set<string>>(new Set());
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  
  // Track highlighted items
  const [approvedHighlightedItems, setApprovedHighlightedItems] = useState<Set<number>>(new Set());
  
  // Track background info
  const [approvedBackgroundInfo, setApprovedBackgroundInfo] = useState<Set<string>>(new Set());

  // Format snake_case and kebab-case to Title Case for display
  const formatFieldName = (key: string): string => {
    return key
      .replace(/[-_]/g, ' ')  // Replace both dashes and underscores with spaces
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const validTypes = ['.pdf', '.xlsx', '.xls', '.xlsm', '.xlsb', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      
      if (!validTypes.includes(fileExt)) {
        setError('Please upload a PDF, Excel, or Image file');
        return;
      }

      setSelectedFile(file);
      setError(null);
      setExtractedData(null);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      const validTypes = ['.pdf', '.xlsx', '.xls', '.xlsm', '.xlsb', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      
      if (!validTypes.includes(fileExt)) {
        setError('Please upload a PDF, Excel, or Image file');
        return;
      }

      setSelectedFile(file);
      setError(null);
      setExtractedData(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const data = await api.postForm<ExtractedData>('/api/extract', formData);

      if (!data.success) {
        throw new Error('Extraction failed');
      }

      setExtractedData(data);
      setEditedFields({});
      setApprovedFields(new Set());
      setApprovedHighlightedItems(new Set());
      setApprovedBackgroundInfo(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to extract data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleEditField = (key: string, currentValue: string) => {
    setEditingField(key);
    setEditValue(editedFields[key] || currentValue);
  };

  const handleSaveField = (key: string) => {
    setEditedFields({
      ...editedFields,
      [key]: editValue
    });
    setEditingField(null);
  };

  const handleCancelEdit = () => {
    setEditingField(null);
    setEditValue("");
  };

  const handleApproveField = (key: string) => {
    const newApproved = new Set(approvedFields);
    if (newApproved.has(key)) {
      newApproved.delete(key);
    } else {
      newApproved.add(key);
    }
    setApprovedFields(newApproved);
  };

  const getFieldValue = (key: string, originalValue: string) => {
    return editedFields[key] !== undefined ? editedFields[key] : originalValue;
  };

  const handleApproveAll = () => {
    if (!extractedData || !extractedData.data) return;
    const allKeys = Object.keys(extractedData.data.form_fields || {});
    setApprovedFields(new Set(allKeys));
  };

  const handleTransferAgents = async () => {
    if (!extractedData || !extractedData.data) return;
    
    setTransferring(true);
    setError(null);
    setTransferSuccess(null);

    try {
      // Get all form fields (approved or not) to ensure we have name/npn
      const allFormFields: Record<string, string> = {};
      Object.entries(extractedData.data.form_fields || {}).forEach(([key, value]) => {
        allFormFields[key] = getFieldValue(key, value);
      });

      // Log what we're sending for debugging
      console.log('Sending form fields:', allFormFields);

      // Call transfer API
      const response = await api.post('/api/admin/transfer-from-document', {
        form_fields: allFormFields,
        carriers: ["1", "2"], // Default carriers - can be made configurable
        states: [], // Will use license states from form or defaults
        transfer_immediately: true
      });

      if (response.success) {
        setTransferSuccess(`Agent created successfully! ID: ${response.advisor_id}`);
        
        // Navigate to agent list after 2 seconds
        setTimeout(() => {
          navigate('/');
        }, 2000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to transfer agent. Please try again.');
    } finally {
      setTransferring(false);
    }
  };

  const handleExportApproved = () => {
    if (!extractedData || !extractedData.data) return;
    
    const approvedData: Record<string, string> = {};
    Array.from(approvedFields).forEach((key) => {
      approvedData[key] = getFieldValue(key, extractedData.data?.form_fields?.[key] || '');
    });

    const exportData = {
      filename: extractedData.filename,
      approved_fields: approvedData,
      highlighted_items: extractedData.data?.highlighted_items || [],
      background_info: extractedData.data?.background_info || {},
      confidence: extractedData.confidence,
      pages_analyzed: extractedData.pages_analyzed,
      approved_count: approvedFields.size,
      total_count: Object.keys(extractedData.data?.form_fields || {}).length
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `approved_data_${extractedData.filename.replace(/\.[^/.]+$/, '')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = () => {
    if (extractedData) {
      navigator.clipboard.writeText(JSON.stringify(extractedData, null, 2));
      alert('JSON copied to clipboard!');
    }
  };

  return (
    <>
      <AppBar position="static" elevation={0} sx={{ bgcolor: "#003366" }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 700, color: "#fff" }}>
            Upload Document
          </Typography>
          <Button color="inherit" component={Link} to="/" startIcon={<List />}>
            Dashboard
          </Button>
          <Button color="inherit" component={Link} to="/request" startIcon={<AddCircle />}>
            New request
          </Button>
          <Button color="inherit" component={Link} to="/advisors/new" startIcon={<PersonAdd />}>
            New agent
          </Button>
          <Button color="inherit" component={Link} to="/pending-transfers" startIcon={<List />}>
            Pending
          </Button>
        </Toolbar>
      </AppBar>

      <main className="min-h-screen" style={{ backgroundColor: "#f5f5f5" }}>
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Box className="mb-6">
            <Typography variant="h4" fontWeight="bold" color="text.primary">
              Upload Document
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Upload a PDF, Excel, or Image file to extract structured data using AI
            </Typography>
          </Box>

        {/* Upload Section */}
        <Card className="mb-8">
          <CardContent>
            <Typography variant="h6" className="font-bold mb-6">
              Upload Document
            </Typography>

            <Box
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input')?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center cursor-pointer transition-all"
              sx={{
                backgroundColor: selectedFile ? '#e6f0f5' : '#f9fafb',
                borderColor: selectedFile ? '#003366' : '#d1d5db',
                '&:hover': {
                  borderColor: '#003366',
                  backgroundColor: '#e6f0f5',
                }
              }}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf,.xlsx,.xls,.xlsm,.xlsb,.jpg,.jpeg,.png,.gif,.bmp,.tiff,.webp"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              <CloudUpload sx={{ fontSize: 48, color: '#003366', mb: 1 }} />
              <Typography variant="body1" className="font-semibold mb-1">
                {selectedFile ? selectedFile.name : 'Drag & drop your file here'}
              </Typography>
              <Typography variant="body2" className="text-gray-500">
                or click to browse (PDF, Excel, or Image files)
              </Typography>
            </Box>

            {error && (
              <Alert severity="error" className="mt-4" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}

            {transferSuccess && (
              <Alert severity="success" className="mt-4" onClose={() => setTransferSuccess(null)}>
                {transferSuccess}
              </Alert>
            )}

            <Box className="flex justify-center gap-3 mt-6">
              <Button
                variant="outlined"
                onClick={() => navigate("/")}
                disabled={loading}
                sx={{ borderColor: "#003366", color: "#003366" }}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                disabled={!selectedFile || loading}
                onClick={handleUpload}
                startIcon={loading ? <CircularProgress size={20} /> : <Description />}
                sx={{ bgcolor: "#003366", '&:hover': { bgcolor: "#002244" } }}
              >
                {loading ? 'Extracting Data...' : 'Extract Data'}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Results Section */}
        {extractedData && extractedData.data && (
          <Card>
            <CardContent>
              <Box className="flex justify-between items-center mb-4">
                <Typography variant="h6" className="font-bold">
                  Extracted Data
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={copyToClipboard}
                >
                  Copy JSON
                </Button>
              </Box>

              {/* Statistics */}
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(2, 1fr)",
                    md: "repeat(4, 1fr)",
                  },
                  gap: 2,
                  mb: 4,
                }}
              >
                <Card sx={{ backgroundColor: '#e3f2fd' }}>
                  <CardContent className="flex flex-col items-center gap-2">
                    <Description sx={{ fontSize: 32, color: '#1976d2' }} />
                    <Typography variant="body2" className="text-gray-600">
                      Form Fields
                    </Typography>
                    <Typography variant="h4" className="font-bold">
                      {Object.keys(extractedData.data?.form_fields || {}).length}
                    </Typography>
                  </CardContent>
                </Card>
                <Card sx={{ backgroundColor: '#f1f8f4' }}>
                  <CardContent className="flex flex-col items-center gap-2">
                    <CheckCircle sx={{ fontSize: 32, color: '#4CAF50' }} />
                    <Typography variant="body2" className="text-gray-600">
                      Agent Carriers
                    </Typography>
                    <Typography variant="h4" className="font-bold">
                      {(extractedData.data?.highlighted_items || []).length}
                    </Typography>
                  </CardContent>
                </Card>
                <Card sx={{ backgroundColor: '#fff3e0' }}>
                  <CardContent className="flex flex-col items-center gap-2">
                    <Check sx={{ fontSize: 32, color: '#ff9800' }} />
                    <Typography variant="body2" className="text-gray-600">
                      Background Info
                    </Typography>
                    <Typography variant="h4" className="font-bold">
                      {Object.keys(extractedData.data?.background_info || {}).length}
                    </Typography>
                  </CardContent>
                </Card>
                <Card sx={{ backgroundColor: '#f3e5f5' }}>
                  <CardContent className="flex flex-col items-center gap-2">
                    <Description sx={{ fontSize: 32, color: '#9c27b0' }} />
                    <Typography variant="body2" className="text-gray-600">
                      Pages Analyzed
                    </Typography>
                    <Typography variant="h4" className="font-bold">
                      {extractedData.pages_analyzed || 0}
                    </Typography>
                  </CardContent>
                </Card>
              </Box>

              {/* Metadata */}
              <Box className="mb-4 flex gap-2 flex-wrap">
                <Chip
                  icon={<CheckCircle />}
                  label={`Confidence: ${(extractedData.confidence * 100).toFixed(0)}%`}
                  color="success"
                />
              </Box>

              {/* Form Fields */}
              {Object.keys(extractedData.data?.form_fields || {}).length > 0 && (
                <Box className="mb-4">
                  <Box className="flex justify-between items-center mb-2">
                    <Typography variant="subtitle1" className="font-semibold">
                      Form Fields ({approvedFields.size}/{Object.keys(extractedData.data?.form_fields || {}).length} approved)
                    </Typography>
                    <Box className="flex gap-2">
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={handleApproveAll}
                        startIcon={<CheckCircle />}
                        sx={{ borderColor: "#003366", color: "#003366" }}
                      >
                        Approve All
                      </Button>
                      <Button
                        size="small"
                        variant="contained"
                        onClick={handleTransferAgents}
                        disabled={approvedFields.size === 0 || transferring}
                        startIcon={transferring ? <CircularProgress size={16} color="inherit" /> : undefined}
                        sx={{ bgcolor: "#003366", '&:hover': { bgcolor: "#002244" } }}
                      >
                        {transferring ? 'Transferring...' : 'Transfer Agent'}
                      </Button>
                    </Box>
                  </Box>
                  <Box className="space-y-2">
                    {Object.entries(extractedData.data?.form_fields || {}).map(([key, value]) => {
                      const isEditing = editingField === key;
                      const isApproved = approvedFields.has(key);
                      const displayValue = getFieldValue(key, value);
                      const isModified = editedFields[key] !== undefined;

                      return (
                        <Card
                          key={key}
                          sx={{
                            backgroundColor: isApproved ? '#e8f5e9' : 'white',
                            border: '1px solid',
                            borderColor: isApproved ? '#4caf50' : '#e0e0e0',
                            mb: 1,
                          }}
                        >
                          <CardContent>
                            <Box className="flex justify-between items-start gap-2">
                              <Box className="flex-1">
                                <Box className="flex items-center gap-2 mb-1">
                                  <Typography variant="body2" fontWeight="600" color="text.primary">
                                    {formatFieldName(key)}
                                  </Typography>
                                  {isModified && (
                                    <Chip label="Modified" size="small" color="info" />
                                  )}
                                  {isApproved && (
                                    <Chip
                                      icon={<CheckCircle />}
                                      label="Approved"
                                      size="small"
                                      color="success"
                                    />
                                  )}
                                </Box>
                                
                                {isEditing ? (
                                  <Box className="flex gap-2 items-center mt-2">
                                    <TextField
                                      fullWidth
                                      size="small"
                                      value={editValue}
                                      onChange={(e) => setEditValue(e.target.value)}
                                      autoFocus
                                      onKeyPress={(e) => {
                                        if (e.key === 'Enter') {
                                          handleSaveField(key);
                                        }
                                      }}
                                    />
                                    <IconButton
                                      size="small"
                                      color="primary"
                                      onClick={() => handleSaveField(key)}
                                    >
                                      <Save />
                                    </IconButton>
                                    <IconButton
                                      size="small"
                                      onClick={handleCancelEdit}
                                    >
                                      <Cancel />
                                    </IconButton>
                                  </Box>
                                ) : (
                                  <Typography variant="body2" className="text-gray-900 ml-0 mt-1">
                                    {displayValue || "(empty)"}
                                  </Typography>
                                )}
                              </Box>

                              {!isEditing && (
                                <Box className="flex gap-1">
                                  <Tooltip title="Edit field">
                                    <IconButton
                                      size="small"
                                      onClick={() => handleEditField(key, displayValue)}
                                    >
                                      <Edit fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                  <Tooltip title={isApproved ? "Unapprove" : "Approve"}>
                                    <IconButton
                                      size="small"
                                      color={isApproved ? "success" : "default"}
                                      onClick={() => handleApproveField(key)}
                                    >
                                      <Check fontSize="small" />
                                    </IconButton>
                                  </Tooltip>
                                </Box>
                              )}
                            </Box>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </Box>
                </Box>
              )}

              {/* Agent Carriers */}
              {(extractedData.data?.highlighted_items || []).length > 0 && (
                <Box className="mb-4">
                  <Box className="flex justify-between items-center mb-2">
                    <Typography variant="subtitle1" className="font-semibold">
                      Agent Carriers ({approvedHighlightedItems.size}/{(extractedData.data?.highlighted_items || []).length} approved)
                    </Typography>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => {
                        setApprovedHighlightedItems(
                          new Set((extractedData.data?.highlighted_items || []).map((_, i) => i))
                        );
                      }}
                      startIcon={<CheckCircle />}
                    >
                      Approve All
                    </Button>
                  </Box>
                  <Box className="flex gap-2 flex-wrap">
                    {(extractedData.data?.highlighted_items || []).map((item, index) => {
                      const isApproved = approvedHighlightedItems.has(index);
                      return (
                        <Chip
                          key={index}
                          label={item}
                          color={isApproved ? "success" : "warning"}
                          icon={isApproved ? <CheckCircle /> : undefined}
                          onClick={() => {
                            const newApproved = new Set(approvedHighlightedItems);
                            if (newApproved.has(index)) {
                              newApproved.delete(index);
                            } else {
                              newApproved.add(index);
                            }
                            setApprovedHighlightedItems(newApproved);
                          }}
                          sx={{ cursor: 'pointer' }}
                        />
                      );
                    })}
                  </Box>
                </Box>
              )}

              {/* Background Info */}
              {Object.keys(extractedData.data?.background_info || {}).length > 0 && (
                <Box className="mb-4">
                  <Box className="flex justify-between items-center mb-2">
                    <Typography variant="subtitle1" className="font-semibold">
                      Background Information ({approvedBackgroundInfo.size}/{Object.keys(extractedData.data?.background_info || {}).length} approved)
                    </Typography>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => {
                        setApprovedBackgroundInfo(
                          new Set(Object.keys(extractedData.data?.background_info || {}))
                        );
                      }}
                      startIcon={<CheckCircle />}
                    >
                      Approve All
                    </Button>
                  </Box>
                  <Box className="space-y-2">
                    {Object.entries(extractedData.data?.background_info || {}).map(([key, value]) => {
                      const isApproved = approvedBackgroundInfo.has(key);
                      const displayValue = value;

                      return (
                        <Card
                          key={key}
                          sx={{
                            backgroundColor: isApproved ? '#e8f5e9' : 'white',
                            border: '1px solid',
                            borderColor: isApproved ? '#4caf50' : '#e0e0e0',
                          }}
                        >
                          <CardContent>
                            <Box className="flex justify-between items-center">
                              <Box className="flex-1">
                                <Typography variant="body2" fontWeight="600" color="text.primary">
                                  {formatFieldName(key)}:
                                </Typography>
                                <Box className="flex items-center gap-2 mt-1">
                                  <Typography variant="body2" className="text-gray-900">
                                    {displayValue}
                                  </Typography>
                                  {isApproved && (
                                    <Chip
                                      icon={<CheckCircle />}
                                      label="Approved"
                                      size="small"
                                      color="success"
                                    />
                                  )}
                                </Box>
                              </Box>
                              <Tooltip title={isApproved ? "Unapprove" : "Approve"}>
                                <IconButton
                                  size="small"
                                  color={isApproved ? "success" : "default"}
                                  onClick={() => {
                                    const newApproved = new Set(approvedBackgroundInfo);
                                    if (newApproved.has(key)) {
                                      newApproved.delete(key);
                                    } else {
                                      newApproved.add(key);
                                    }
                                    setApprovedBackgroundInfo(newApproved);
                                  }}
                                >
                                  <Check />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        )}
      </Container>
    </main>
    </>
  );
}
