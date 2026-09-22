export type SubmissionStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED';

export interface ExternalParticipantInput {
  name: string;
  usn: string;
  email: string;
  phone?: string;
  role?: 'Leader' | 'Member';
}

export interface ExternalRegistrationInput {
  submission_id?: string;
  team_name: string;
  leader?: ExternalParticipantInput;
  members?: ExternalParticipantInput[];
  consent_given: boolean;
  source?: 'google_forms' | 'public_web';
}

export interface Submission {
  id: string;
  source: string;
  external_submission_id: string;
  team_name: string;
  leader_name: string;
  leader_usn: string;
  leader_email: string;
  leader_phone?: string;
  members_count: number;
  consent_given: boolean;
  status: SubmissionStatus;
  error_message?: string;
  created_team_id?: string;
  raw_payload: {
    team_name: string;
    members: ExternalParticipantInput[];
    consent_given: boolean;
    original_payload?: any;
  };
  auto_approved: boolean;
  submitted_at: string;
  processed_at?: string;
  reviewed_by?: string;
}

export interface SubmissionMetrics {
  total_submissions: number;
  accepted_count: number;
  pending_count: number;
  rejected_count: number;
  last_submission_at?: string;
  last_sync_at?: string;
}

export interface IntegrationSettings {
  webhook_url: string;
  webhook_secret: string;
  registration_auto_approve: boolean;
  public_registration_open: boolean;
  metrics: SubmissionMetrics;
}

export interface IntegrationSettingsUpdate {
  registration_auto_approve?: boolean;
  public_registration_open?: boolean;
  regenerate_secret?: boolean;
}
