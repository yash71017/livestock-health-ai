import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, FormControl, InputLabel,
  Select, MenuItem, Chip, Button, Alert, CircularProgress, Grid
} from '@mui/material';
import HealingOutlinedIcon from '@mui/icons-material/HealingOutlined';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import { animalAPI, diagnosisAPI, vocabAPI } from '../services/api';

const SUCCESS = '#2E7D5B';
const WARNING = '#C77D34';
const DANGER = '#B4432C';
const PINE_LIGHT = '#3C7A68';
const THRESHOLD = 25; // matches backend min_confidence_threshold

// confidence → colour + label
function confLevel(conf) {
  if (conf >= 60) return { color: SUCCESS, label: 'Moderate confidence — verify with a veterinarian' };
  if (conf >= THRESHOLD) return { color: WARNING, label: 'Limited confidence — veterinary consultation recommended' };
  return { color: DANGER, label: 'Below confidence threshold — veterinary consultation recommended' };
}

// ── Signature element: the confidence meter ──
function ConfidenceMeter({ confidence }) {
  const { color, label } = confLevel(confidence);
  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 1 }}>
        <Typography sx={{ fontSize: 13, color: 'text.secondary', fontWeight: 500 }}>
          Model confidence
        </Typography>
        <Typography sx={{ fontFamily: '"Fraunces", serif', fontSize: 20, fontWeight: 600, color }}>
          {confidence}%
        </Typography>
      </Box>

      {/* zoned track */}
      <Box
        sx={{
          position: 'relative', height: 12, borderRadius: 999, overflow: 'hidden',
          background: 'linear-gradient(90deg, rgba(180,67,44,.18) 0%, rgba(199,125,52,.18) 45%, rgba(46,125,91,.18) 100%)',
        }}
      >
        {/* threshold marker */}
        <Box sx={{ position: 'absolute', top: -3, bottom: -3, width: 2, left: `${THRESHOLD}%`, backgroundColor: 'rgba(27,36,31,.28)' }} />
        {/* fill */}
        <Box sx={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${Math.min(confidence, 100)}%`, borderRadius: 999, backgroundColor: color, transition: 'width .5s ease' }} />
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.6, opacity: 0.7 }}>
        <Typography sx={{ fontSize: 10.5, color: 'text.secondary' }}>uncertain</Typography>
        <Typography sx={{ fontSize: 10.5, color: 'text.secondary' }}>▲ {THRESHOLD}% threshold</Typography>
        <Typography sx={{ fontSize: 10.5, color: 'text.secondary' }}>confident</Typography>
      </Box>
      <Typography sx={{ fontSize: 12, color: 'text.secondary', mt: 1 }}>{label}</Typography>
    </Box>
  );
}

function DiagnosisPage() {
  const [animals, setAnimals] = useState([]);
  const [symptoms, setSymptoms] = useState([]);
  const [selectedAnimal, setSelectedAnimal] = useState('');
  const [selectedSymptoms, setSelectedSymptoms] = useState([]);
  const [diagnosis, setDiagnosis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Load animals and symptom vocabulary from backend
    animalAPI.getAll()
      .then((res) => setAnimals(res.data || []))
      .catch(() => {});

    vocabAPI.getVocab()
      .then((res) => setSymptoms(res.data?.symptoms || []))
      .catch(() => {
        // Fallback to constants if API is down
        import('../utils/constants').then((mod) => setSymptoms(mod.SYMPTOMS));
      });
  }, []);

  const handleSymptomToggle = (symptom) => {
    setSelectedSymptoms((prev) =>
      prev.includes(symptom) ? prev.filter((s) => s !== symptom) : [...prev, symptom]
    );
  };

  const handleDiagnose = async () => {
    if (selectedSymptoms.length === 0) {
      setError('Please select at least one symptom');
      return;
    }

    setLoading(true);
    setError('');
    setDiagnosis(null);

    try {
      const res = await diagnosisAPI.diagnose({
        animalId: selectedAnimal || undefined,
        symptoms: selectedSymptoms,
      });
      setDiagnosis(res.data);
    } catch (err) {
      setError('Diagnosis failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedAnimal('');
    setSelectedSymptoms([]);
    setDiagnosis(null);
    setError('');
  };

  // Header appearance depends on confidence / whether it's an "uncertain" result
  const isUncertain = diagnosis && (diagnosis.confidence < THRESHOLD
    || /uncertain|consult|unknown|rare/i.test(diagnosis.disease));
  const headerColor = diagnosis ? confLevel(diagnosis.confidence).color : SUCCESS;
  const topConf = diagnosis?.allPredictions?.[0]?.confidence || 100;

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3}>
        {/* Input panel */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography sx={{ fontSize: 15, fontWeight: 700, mb: 1.5 }}>
                Select animal <Box component="span" sx={{ color: 'text.secondary', fontWeight: 400 }}>(optional)</Box>
              </Typography>
              <FormControl fullWidth sx={{ mb: 3 }} size="small">
                <InputLabel>Animal</InputLabel>
                <Select
                  value={selectedAnimal}
                  onChange={(e) => setSelectedAnimal(e.target.value)}
                  label="Animal"
                >
                  <MenuItem value="">None (symptoms only)</MenuItem>
                  {animals.map((a) => (
                    <MenuItem key={a.id} value={a.id}>
                      {a.id} — {a.type} / {a.breed} (Age: {a.age})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Typography sx={{ fontSize: 15, fontWeight: 700, mb: 1.5 }}>
                Observed symptoms
              </Typography>
              <Box sx={{ mb: 2.5, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {symptoms.map((s) => {
                  const on = selectedSymptoms.includes(s);
                  return (
                    <Chip
                      key={s}
                      label={s}
                      onClick={() => handleSymptomToggle(s)}
                      clickable
                      variant={on ? 'filled' : 'outlined'}
                      color={on ? 'primary' : 'default'}
                    />
                  );
                })}
              </Box>

              {selectedSymptoms.length > 0 && (
                <Typography variant="body2" sx={{ mb: 2 }} color="text.secondary">
                  {selectedSymptoms.length} selected
                </Typography>
              )}

              <Box sx={{ display: 'flex', gap: 1.5 }}>
                <Button
                  variant="contained"
                  onClick={handleDiagnose}
                  disabled={loading || selectedSymptoms.length === 0}
                  size="large"
                  startIcon={!loading && <HealingOutlinedIcon />}
                >
                  {loading ? <CircularProgress size={22} color="inherit" /> : 'Get diagnosis'}
                </Button>
                <Button variant="outlined" color="inherit" onClick={handleReset} size="large">
                  Reset
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Results panel */}
        <Grid item xs={12} md={6}>
          {/* Empty state */}
          {!diagnosis && !loading && (
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', minHeight: 320, color: 'text.secondary' }}>
                <Box sx={{ width: 56, height: 56, borderRadius: '14px', backgroundColor: 'rgba(31,82,68,.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 2 }}>
                  <HealingOutlinedIcon sx={{ fontSize: 28, color: 'primary.main' }} />
                </Box>
                <Typography sx={{ fontWeight: 600, color: 'text.primary', mb: 0.5 }}>
                  No diagnosis yet
                </Typography>
                <Typography variant="body2" sx={{ maxWidth: 280 }}>
                  Select the symptoms you've observed, then run a diagnosis to see the model's assessment.
                </Typography>
              </CardContent>
            </Card>
          )}

          {loading && (
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 320 }}>
                <CircularProgress />
              </CardContent>
            </Card>
          )}

          {diagnosis && !loading && (
            <Card>
              <CardContent>
                {/* Result header */}
                <Box
                  sx={{
                    display: 'flex', alignItems: 'center', gap: 1.25,
                    backgroundColor: isUncertain ? 'rgba(199,125,52,.10)' : 'rgba(46,125,91,.10)',
                    border: '1px solid',
                    borderColor: isUncertain ? 'rgba(199,125,52,.25)' : 'rgba(46,125,91,.25)',
                    borderRadius: '12px', px: 2, py: 1.75, mb: 2.5,
                  }}
                >
                  {isUncertain
                    ? <WarningAmberRoundedIcon sx={{ color: WARNING }} />
                    : <CheckCircleOutlineRoundedIcon sx={{ color: SUCCESS }} />}
                  <Box>
                    <Typography sx={{ fontSize: 11, color: 'text.secondary', fontWeight: 500, lineHeight: 1 }}>
                      Predicted condition
                    </Typography>
                    <Typography sx={{ fontSize: 17, fontWeight: 700, mt: 0.3 }}>
                      {diagnosis.disease}
                    </Typography>
                  </Box>
                </Box>

                {/* Signature confidence meter */}
                <ConfidenceMeter confidence={diagnosis.confidence} />

                {/* Top predictions with mini bars */}
                {diagnosis.allPredictions && diagnosis.allPredictions.length > 0 && (
                  <Box sx={{ mt: 2.5 }}>
                    <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 1 }}>
                      Top predictions
                    </Typography>
                    {diagnosis.allPredictions.map((p, i) => (
                      <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 0.9, borderBottom: i < diagnosis.allPredictions.length - 1 ? '1px solid' : 'none', borderColor: 'divider' }}>
                        <Typography sx={{ flex: 1, fontSize: 13.5 }}>{p.disease}</Typography>
                        <Box sx={{ width: 90, height: 6, borderRadius: 999, backgroundColor: 'rgba(27,36,31,.08)', overflow: 'hidden' }}>
                          <Box sx={{ height: '100%', width: `${(p.confidence / topConf) * 100}%`, backgroundColor: PINE_LIGHT }} />
                        </Box>
                        <Typography sx={{ fontSize: 13, color: 'text.secondary', width: 46, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                          {p.confidence}%
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                )}

                {/* Graph enrichment */}
                {diagnosis.graphInfo?.commonSymptoms?.length > 0 && (
                  <Box sx={{ mt: 2.5, p: 2, borderRadius: '12px', backgroundColor: 'rgba(31,82,68,.04)', border: '1px solid', borderColor: 'divider' }}>
                    <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 1 }}>
                      Typical symptoms for {diagnosis.disease}
                      <Box component="span" sx={{ fontWeight: 400, color: 'text.secondary', ml: 0.5 }}>
                        · from knowledge graph
                      </Box>
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                      {diagnosis.graphInfo.commonSymptoms.map((s, i) => (
                        <Chip key={i} label={`${s.symptom} · ${s.frequency}×`} size="small" variant="outlined" />
                      ))}
                    </Box>
                    {diagnosis.graphInfo.knownCases > 0 && (
                      <Typography variant="caption" display="block" sx={{ mt: 1.25, color: 'text.secondary' }}>
                        {diagnosis.graphInfo.knownCases} known case{diagnosis.graphInfo.knownCases === 1 ? '' : 's'} in the database
                      </Typography>
                    )}
                  </Box>
                )}

                {/* Disclaimer */}
                <Alert severity="warning" sx={{ mt: 2.5 }}>
                  <Typography variant="caption">{diagnosis.disclaimer}</Typography>
                </Alert>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}

export default DiagnosisPage;
