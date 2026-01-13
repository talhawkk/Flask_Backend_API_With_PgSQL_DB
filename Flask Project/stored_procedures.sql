
DROP FUNCTION IF EXISTS get_monthly_sales_report(INTEGER, INTEGER);

CREATE OR REPLACE FUNCTION get_monthly_sales_report(
    report_year INTEGER,
    report_month INTEGER
)
RETURNS TABLE (
    total_orders BIGINT,
    total_revenue NUMERIC,
    completed_orders BIGINT,
    pending_orders BIGINT,
    cancelled_orders BIGINT,
    avg_order_value NUMERIC,
    top_product_id INTEGER,
    top_product_name VARCHAR,
    top_product_sales BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH monthly_orders AS (
        SELECT * FROM "order"
        WHERE EXTRACT(YEAR FROM created_at) = report_year
        AND EXTRACT(MONTH FROM created_at) = report_month
    ),
    order_stats AS (
        SELECT 
            COUNT(*)::BIGINT as total_orders,
            COALESCE(SUM(CASE WHEN status = 'completed' THEN total_amount ELSE 0 END), 0)::NUMERIC as total_revenue,
            COUNT(*) FILTER (WHERE status = 'completed')::BIGINT as completed_orders,
            COUNT(*) FILTER (WHERE status = 'pending')::BIGINT as pending_orders,
            COUNT(*) FILTER (WHERE status = 'cancelled')::BIGINT as cancelled_orders,
            COALESCE(AVG(CASE WHEN status = 'completed' THEN total_amount END), 0)::NUMERIC as avg_order_value
        FROM monthly_orders
    ),
    top_product AS (
        SELECT 
            p.id as product_id,
            p.name::VARCHAR as product_name,
            COALESCE(SUM(oi.quantity), 0)::BIGINT as total_sold
        FROM order_item oi
        JOIN "order" o ON oi.order_id = o.id
        JOIN product p ON oi.product_id = p.id
        WHERE EXTRACT(YEAR FROM o.created_at) = report_year
        AND EXTRACT(MONTH FROM o.created_at) = report_month
        AND o.status = 'completed'
        GROUP BY p.id, p.name
        ORDER BY total_sold DESC
        LIMIT 1
    )
    SELECT 
        os.total_orders,
        os.total_revenue,
        os.completed_orders,
        os.pending_orders,
        os.cancelled_orders,
        os.avg_order_value,
        tp.product_id,
        tp.product_name,
        tp.total_sold
    FROM order_stats os
    LEFT JOIN top_product tp ON true;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_daily_sales_report(
    report_date DATE
)
RETURNS TABLE (
    total_orders BIGINT,
    total_revenue NUMERIC,
    completed_orders BIGINT,
    pending_orders BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_orders,
        COALESCE(SUM(CASE WHEN status = 'completed' THEN total_amount ELSE 0 END), 0)::NUMERIC as total_revenue,
        COUNT(*) FILTER (WHERE status = 'completed')::BIGINT as completed_orders,
        COUNT(*) FILTER (WHERE status = 'pending')::BIGINT as pending_orders
    FROM "order"
    WHERE DATE(created_at) = report_date;
END;
$$ LANGUAGE plpgsql;


-- User Order Summary
CREATE OR REPLACE FUNCTION get_user_order_summary(
    user_email_param VARCHAR
)
RETURNS TABLE (
    user_id INTEGER,
    total_orders BIGINT,
    total_spent NUMERIC,
    avg_order_value NUMERIC,
    last_order_date TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id::INTEGER as user_id,
        COUNT(o.id)::BIGINT as total_orders,
        COALESCE(SUM(o.total_amount), 0)::NUMERIC as total_spent,
        COALESCE(AVG(o.total_amount), 0)::NUMERIC as avg_order_value,
        MAX(o.created_at)::TIMESTAMP as last_order_date
    FROM "user" u
    LEFT JOIN "order" o ON u.id = o.user_id AND o.status = 'completed'
    WHERE u.email = user_email_param
    GROUP BY u.id;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- Indexes for query optimization
-- ============================================
-- These are created by SQLAlchemy, but you can add more here if needed

-- Composite index for order filtering
CREATE INDEX IF NOT EXISTS idx_order_user_status ON "order" (user_id, status);

-- Index for payment status filtering
CREATE INDEX IF NOT EXISTS idx_payment_status_date ON payment (status, created_at);

-- Index for audit log filtering
CREATE INDEX IF NOT EXISTS idx_audit_table_action ON audit_log (table_name, action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log (created_at DESC);


