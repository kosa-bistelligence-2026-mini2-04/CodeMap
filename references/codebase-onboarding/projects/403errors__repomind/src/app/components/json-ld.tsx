import JsonLdScript from "@/components/JsonLdScript";
import { buildRootStructuredData } from "@/lib/structured-data";

export default function JsonLd() {
    return <JsonLdScript data={buildRootStructuredData()} />;
}
