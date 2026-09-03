-- Incremental fix for existing databases (Phase1-3 P1 review)
CREATE UNIQUE INDEX IF NOT EXISTS uk_wo_analysis_active
    ON maintenance_work_order (analysis_id)
    WHERE status <> 'CANCELLED';
