export interface DecisionInput { alert_id: string; option_id: string; action: 'approve' | 'reject'; operator: string }
export interface ControlInput { action: 'pause' | 'resume' | 'speed' | 'reset'; value?: number }
export interface InjectInput { type: 'buoy_down' | 'buoy_up' | 'network_down' | 'network_up' | 'noise_up' | 'noise_down'; target?: string }
