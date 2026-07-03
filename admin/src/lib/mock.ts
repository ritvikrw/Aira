export interface Client {
  id: string
  name: string
  slug: string
  email: string
  sarvam_key: string | null
  cartesia_key: string | null
  openai_key: string | null
  google_key: string | null
  elevenlabs_key: string | null
  is_active: boolean
  created_at: string
  total_calls: number
  calls_today: number
  active_calls: number
}

export interface CallLog {
  session_id: string
  caller_name: string | null
  caller_phone: string | null
  status: 'active' | 'ended'
  call_duration_seconds: number | null
  call_category: string | null
  call_start_time: string
}

export const MOCK_CLIENTS: Client[] = [
  {
    id: 'c1a2b3c4-0001-0000-0000-000000000001',
    name: 'Acme Corp',
    slug: 'acme',
    email: 'admin@acmecorp.com',
    sarvam_key: 'sk-sarvam-acme-xxxxxxxxxxxx',
    cartesia_key: 'sk-cartesia-acme-xxxxxxxxxx',
    openai_key: null,
    google_key: 'AIza-acme-xxxxxxxxxxxxxxxxxxxx',
    elevenlabs_key: null,
    is_active: true,
    created_at: '2026-05-10T09:00:00Z',
    total_calls: 312,
    calls_today: 18,
    active_calls: 2,
  },
  {
    id: 'c1a2b3c4-0002-0000-0000-000000000002',
    name: 'Apollo Hospital',
    slug: 'apollo',
    email: 'admin@apollohospital.com',
    sarvam_key: 'sk-sarvam-apollo-xxxxxxxxxxxx',
    cartesia_key: null,
    openai_key: 'sk-openai-apollo-xxxxxxxxxxxx',
    google_key: null,
    elevenlabs_key: null,
    is_active: true,
    created_at: '2026-05-18T11:30:00Z',
    total_calls: 874,
    calls_today: 41,
    active_calls: 5,
  },
  {
    id: 'c1a2b3c4-0003-0000-0000-000000000003',
    name: 'Zomato Support',
    slug: 'zomato',
    email: 'admin@zomato.com',
    sarvam_key: 'sk-sarvam-zomato-xxxxxxxxxxxx',
    cartesia_key: 'sk-cartesia-zomato-xxxxxxxxxx',
    openai_key: 'sk-openai-zomato-xxxxxxxxxxxx',
    google_key: null,
    elevenlabs_key: 'el-zomato-xxxxxxxxxxxx',
    is_active: true,
    created_at: '2026-06-01T08:00:00Z',
    total_calls: 1540,
    calls_today: 93,
    active_calls: 11,
  },
  {
    id: 'c1a2b3c4-0004-0000-0000-000000000004',
    name: 'Nykaa Beauty',
    slug: 'nykaa',
    email: 'admin@nykaa.com',
    sarvam_key: null,
    cartesia_key: 'sk-cartesia-nykaa-xxxxxxxxxx',
    openai_key: 'sk-openai-nykaa-xxxxxxxxxxxx',
    google_key: null,
    elevenlabs_key: null,
    is_active: false,
    created_at: '2026-06-12T14:00:00Z',
    total_calls: 47,
    calls_today: 0,
    active_calls: 0,
  },
]

export const MOCK_CALLS: Record<string, CallLog[]> = {
  'c1a2b3c4-0001-0000-0000-000000000001': [
    { session_id: 'sess-acme-001', caller_name: 'Rajesh Kumar', caller_phone: '+91 98765 43210', status: 'active', call_duration_seconds: null, call_category: 'Sales', call_start_time: '2026-06-29T09:12:00Z' },
    { session_id: 'sess-acme-002', caller_name: 'Priya Sharma', caller_phone: '+91 87654 32109', status: 'ended', call_duration_seconds: 142, call_category: 'Support', call_start_time: '2026-06-29T08:55:00Z' },
    { session_id: 'sess-acme-003', caller_name: null, caller_phone: '+91 76543 21098', status: 'ended', call_duration_seconds: 87, call_category: 'Enquiry', call_start_time: '2026-06-29T08:20:00Z' },
    { session_id: 'sess-acme-004', caller_name: 'Amit Patel', caller_phone: '+91 65432 10987', status: 'ended', call_duration_seconds: 213, call_category: 'Sales', call_start_time: '2026-06-28T16:40:00Z' },
    { session_id: 'sess-acme-005', caller_name: 'Sneha Reddy', caller_phone: '+91 54321 09876', status: 'ended', call_duration_seconds: 64, call_category: 'Other', call_start_time: '2026-06-28T15:10:00Z' },
  ],
  'c1a2b3c4-0002-0000-0000-000000000002': [
    { session_id: 'sess-apollo-001', caller_name: 'Dr. Mehta', caller_phone: '+91 99887 76655', status: 'active', call_duration_seconds: null, call_category: 'Appointment', call_start_time: '2026-06-29T09:05:00Z' },
    { session_id: 'sess-apollo-002', caller_name: 'Kavitha R', caller_phone: '+91 88776 65544', status: 'active', call_duration_seconds: null, call_category: 'Enquiry', call_start_time: '2026-06-29T09:08:00Z' },
    { session_id: 'sess-apollo-003', caller_name: 'Suresh M', caller_phone: '+91 77665 54433', status: 'ended', call_duration_seconds: 320, call_category: 'Appointment', call_start_time: '2026-06-29T08:30:00Z' },
    { session_id: 'sess-apollo-004', caller_name: null, caller_phone: '+91 66554 43322', status: 'ended', call_duration_seconds: 98, call_category: 'Support', call_start_time: '2026-06-28T17:00:00Z' },
  ],
  'c1a2b3c4-0003-0000-0000-000000000003': [
    { session_id: 'sess-zomato-001', caller_name: 'Ananya S', caller_phone: '+91 93456 78901', status: 'active', call_duration_seconds: null, call_category: 'Order', call_start_time: '2026-06-29T09:15:00Z' },
    { session_id: 'sess-zomato-002', caller_name: 'Vikram T', caller_phone: '+91 82345 67890', status: 'ended', call_duration_seconds: 45, call_category: 'Refund', call_start_time: '2026-06-29T09:10:00Z' },
    { session_id: 'sess-zomato-003', caller_name: null, caller_phone: '+91 71234 56789', status: 'ended', call_duration_seconds: 120, call_category: 'Order', call_start_time: '2026-06-29T09:02:00Z' },
  ],
  'c1a2b3c4-0004-0000-0000-000000000004': [],
}
