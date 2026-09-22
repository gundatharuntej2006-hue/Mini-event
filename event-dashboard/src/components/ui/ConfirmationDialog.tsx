import React from 'react';
import { AlertTriangle, AlertCircle } from 'lucide-react';
import { Modal } from './Modal';
import { Button } from './Button';

interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string | React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  isBlocked?: boolean;
  blockedReason?: string;
}

export function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDestructive = true,
  isLoading = false,
  isBlocked = false,
  blockedReason,
}: ConfirmationDialogProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          {isBlocked ? (
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          )}
          <span>{title}</span>
        </div>
      }
      maxWidth="md"
      footer={
        <>
          <Button variant="outline" size="sm" onClick={onClose} disabled={isLoading}>
            {cancelLabel}
          </Button>
          {!isBlocked && (
            <Button
              variant={isDestructive ? 'danger' : 'primary'}
              size="sm"
              onClick={onConfirm}
              isLoading={isLoading}
            >
              {confirmLabel}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-3 text-xs text-slate-300 font-sans">
        <div>{message}</div>
        {isBlocked && blockedReason && (
          <div className="p-3 bg-amber-950/40 border border-amber-500/30 rounded-xl text-amber-200 font-mono text-[11px] leading-relaxed">
            {blockedReason}
          </div>
        )}
      </div>
    </Modal>
  );
}
