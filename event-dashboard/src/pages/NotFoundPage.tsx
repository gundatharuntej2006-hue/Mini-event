import { Link } from 'react-router-dom';
import { Compass, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/Button';

export function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6">
      <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
        <Compass className="w-8 h-8" />
      </div>
      <h2 className="text-xl font-bold text-slate-900">Module Not Located (404)</h2>
      <p className="text-xs text-slate-500 max-w-sm mt-1 mb-6">
        The requested operations screen does not exist or has not been provisioned in EVENT HQ.
      </p>
      <Link to="/">
        <Button size="sm" leftIcon={<ArrowLeft className="w-4 h-4" />}>
          Return to Operations Overview
        </Button>
      </Link>
    </div>
  );
}
