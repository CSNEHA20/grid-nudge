import { getEvaluationData, getCalibrationData } from "@/lib/data";
import { EvaluationView } from "@/components/EvaluationView";

export default async function EvaluationPage() {
  const [evaluation, calibration] = await Promise.all([
    getEvaluationData(),
    getCalibrationData(),
  ]);

  return <EvaluationView evaluation={evaluation} calibration={calibration} />;
}
