import { callControl, dynamic } from "../control";

export { dynamic };

export async function GET() {
  return callControl("/api/status");
}
