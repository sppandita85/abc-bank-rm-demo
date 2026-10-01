-- ABC Bank RM Assistant seed data
-- ---------- Customers ----------
INSERT INTO customers (customer_id, full_name, email, phone, segment, city, rm_name) VALUES
('C1001', 'Rahul Mehta',      'rahul.mehta@example.com',     '+91-9820011001', 'Premier',  'Mumbai',    'Priya Sharma'),
('C1002', 'Ananya Iyer',      'ananya.iyer@example.com',     '+91-9820011002', 'Priority', 'Chennai',   'Priya Sharma'),
('C1003', 'Vikram Singh',     'vikram.singh@example.com',    '+91-9820011003', 'Premier',  'Delhi',     'Priya Sharma'),
('C1004', 'Sneha Kulkarni',   'sneha.kulkarni@example.com',  '+91-9820011004', 'Classic',  'Pune',      'Priya Sharma'),
('C1005', 'Arjun Nair',       'arjun.nair@example.com',      '+91-9820011005', 'Priority', 'Kochi',     'Priya Sharma'),
('C1006', 'Meera Joshi',      'meera.joshi@example.com',     '+91-9820011006', 'Premier',  'Bengaluru', 'Priya Sharma'),
('C1007', 'Karan Malhotra',   'karan.malhotra@example.com',  '+91-9820011007', 'Classic',  'Gurugram',  'Priya Sharma'),
('C1008', 'Fatima Sheikh',    'fatima.sheikh@example.com',   '+91-9820011008', 'Priority', 'Hyderabad', 'Priya Sharma'),
('C1009', 'Rohan Desai',      'rohan.desai@example.com',     '+91-9820011009', 'Premier',  'Ahmedabad', 'Priya Sharma'),
('C1010', 'Kavya Reddy',      'kavya.reddy@example.com',     '+91-9820011010', 'Classic',  'Hyderabad', 'Priya Sharma');

-- ---------- Accounts ----------
INSERT INTO accounts (account_no, customer_id, account_type, balance, branch, ifsc, opened_on) VALUES
('50100012340001', 'C1001', 'SAVINGS', 1845230.55, 'Mumbai - Bandra West',   'ABCB0000123', '2016-04-12'),
('50200012340002', 'C1001', 'CURRENT', 5230410.00, 'Mumbai - Bandra West',   'ABCB0000123', '2019-08-01'),
('50100012340003', 'C1002', 'SAVINGS',  245880.20, 'Chennai - T Nagar',      'ABCB0000456', '2018-02-20'),
('50100012340004', 'C1003', 'SAVINGS', 3120775.90, 'Delhi - Connaught Place','ABCB0000789', '2014-11-05'),
('50100012340005', 'C1004', 'SALARY',    68420.35, 'Pune - Baner',           'ABCB0000321', '2021-06-15'),
('50100012340006', 'C1005', 'SAVINGS',  512300.00, 'Kochi - MG Road',        'ABCB0000654', '2017-09-09'),
('50100012340007', 'C1006', 'SAVINGS', 2789045.10, 'Bengaluru - Indiranagar','ABCB0000987', '2015-01-25'),
('50100012340008', 'C1007', 'SALARY',    35210.75, 'Gurugram - Cyber City',  'ABCB0000111', '2022-03-03'),
('50100012340009', 'C1008', 'SAVINGS',  402115.60, 'Hyderabad - Banjara Hills','ABCB0000222','2019-12-12'),
('50100012340010', 'C1009', 'SAVINGS', 6120980.00, 'Ahmedabad - SG Highway', 'ABCB0000333', '2013-07-19'),
('50100012340011', 'C1010', 'SAVINGS',   92340.80, 'Hyderabad - Gachibowli', 'ABCB0000444', '2023-05-30');

-- ---------- Transactions (deterministic, generated) ----------
DO $$
DECLARE
    acc RECORD;
    i INT;
    bal NUMERIC(14,2);
    amt NUMERIC(14,2);
    drcr CHAR(2);
    descs TEXT[] := ARRAY['Amazon Pay UPI', 'Swiggy UPI', 'Salary Credit - Employer', 'NEFT to HDFC - Rent',
                          'ATM Withdrawal', 'Electricity Bill - BESCOM', 'IMPS from Family', 'Zomato UPI',
                          'Mutual Fund SIP', 'Credit Card Payment', 'Interest Credit', 'POS - Reliance Retail',
                          'Insurance Premium - LIC', 'Cheque Deposit', 'Flipkart UPI'];
    channels TEXT[] := ARRAY['UPI','UPI','NEFT','NEFT','ATM','BBPS','IMPS','UPI','ECS','NEFT','SYS','POS','ECS','CHQ','UPI'];
    idx INT;
BEGIN
    PERFORM setseed(0.42);
    FOR acc IN SELECT account_no, balance FROM accounts LOOP
        bal := acc.balance;
        FOR i IN 0..14 LOOP
            idx := 1 + floor(random() * 15)::INT;
            IF descs[idx] IN ('Salary Credit - Employer', 'IMPS from Family', 'Interest Credit', 'Cheque Deposit') THEN
                drcr := 'CR';
            ELSE
                drcr := 'DR';
            END IF;
            amt := round((500 + random() * 45000)::NUMERIC, 2);
            INSERT INTO transactions (account_no, txn_date, description, amount, dr_cr, channel, status, reference_no, balance_after)
            VALUES (acc.account_no,
                    date_trunc('minute', now() - (i * INTERVAL '2 days') - (random() * INTERVAL '10 hours')),
                    descs[idx], amt, drcr, channels[idx],
                    CASE WHEN i = 3 AND acc.account_no = '50100012340003' THEN 'FAILED' ELSE 'SUCCESS' END,
                    'REF' || lpad((floor(random() * 1e9))::TEXT, 9, '0'),
                    bal);
            -- walk balance backwards in time
            IF drcr = 'CR' THEN bal := bal - amt; ELSE bal := bal + amt; END IF;
        END LOOP;
    END LOOP;
END $$;

-- A disputed double-debit for Ananya (used by a seeded email)
INSERT INTO transactions (account_no, txn_date, description, amount, dr_cr, channel, status, reference_no, balance_after) VALUES
('50100012340003', now() - INTERVAL '1 day', 'UPI - Croma Electronics', 18999.00, 'DR', 'UPI', 'SUCCESS', 'REF771234501', 245880.20),
('50100012340003', now() - INTERVAL '1 day' + INTERVAL '2 minutes', 'UPI - Croma Electronics', 18999.00, 'DR', 'UPI', 'SUCCESS', 'REF771234502', 226881.20);

-- ---------- Loans ----------
INSERT INTO loans VALUES
('HL0098123', 'C1001', 'Home Loan',     8500000, 6234500.00, 8.50, 73850.00, CURRENT_DATE + 5,  240, 58, 'ACTIVE'),
('PL0045671', 'C1004', 'Personal Loan',  500000,  312400.00, 11.25, 16450.00, CURRENT_DATE + 12, 36, 14, 'ACTIVE'),
('CL0077342', 'C1005', 'Car Loan',      1200000,  845600.00, 9.10, 24950.00, CURRENT_DATE + 8,  60, 18, 'ACTIVE'),
('HL0099441', 'C1006', 'Home Loan',    12000000, 10450000.00, 8.40, 103250.00, CURRENT_DATE + 3, 240, 22, 'ACTIVE'),
('PL0046012', 'C1007', 'Personal Loan',  300000,  254300.00, 12.50, 10050.00, CURRENT_DATE + 15, 36, 5, 'ACTIVE');

-- ---------- Cards ----------
INSERT INTO cards VALUES
('4532-XXXX-XXXX-1001', 'C1001', 'ABC Infinite Credit Card',   1000000, 812450.00, 187550.00, 9377.50, CURRENT_DATE + 9,  48250, 'ACTIVE'),
('4532-XXXX-XXXX-1002', 'C1002', 'ABC Rewards Credit Card',     300000, 241200.00,  58800.00, 2940.00, CURRENT_DATE + 14, 12870, 'ACTIVE'),
('4532-XXXX-XXXX-1003', 'C1003', 'ABC Infinite Credit Card',   1500000, 1390000.00, 110000.00, 5500.00, CURRENT_DATE + 6, 91540, 'ACTIVE'),
('4532-XXXX-XXXX-1008', 'C1008', 'ABC Travel Credit Card',      500000, 468900.00,  31100.00, 1555.00, CURRENT_DATE + 20, 22110, 'BLOCKED'),
('4532-XXXX-XXXX-1010', 'C1010', 'ABC Millennia Credit Card',   150000, 132500.00,  17500.00,  875.00, CURRENT_DATE + 11,  3420, 'ACTIVE');

-- ---------- Fixed deposits ----------
INSERT INTO fixed_deposits VALUES
('FD7700123', 'C1001', 2500000, 7.10, CURRENT_DATE - 350, CURRENT_DATE + 15,  2677500.00, FALSE, 'ACTIVE'),
('FD7700456', 'C1003', 5000000, 7.25, CURRENT_DATE - 200, CURRENT_DATE + 530, 5758000.00, TRUE,  'ACTIVE'),
('FD7700789', 'C1006', 1000000, 7.00, CURRENT_DATE - 90,  CURRENT_DATE + 275, 1070000.00, FALSE, 'ACTIVE'),
('FD7700999', 'C1009', 7500000, 7.40, CURRENT_DATE - 30,  CURRENT_DATE + 700, 8632000.00, TRUE,  'ACTIVE'),
('FD7701001', 'C1002',  300000, 6.90, CURRENT_DATE - 380, CURRENT_DATE - 15,   320700.00, FALSE, 'MATURED');

-- ---------- Products ----------
INSERT INTO products VALUES
('SAV-REG', 'ABC Regular Savings Account', 'SAVINGS', '3.00% p.a. (up to Rs 10L), 3.50% above',
 'Min average monthly balance Rs 10,000 (metro). Non-maintenance charge Rs 500/qtr. 5 free ATM txns/month.',
 'Resident Indian individuals aged 18+ with valid KYC (PAN + Aadhaar).',
 'Free debit card, unlimited UPI, free NEFT/IMPS online, doorstep banking on request.',
 'N/A', 'Rs 10,000 AMB', 'savings account open new basic regular'),
('SAV-PRM', 'ABC Premier Savings Account', 'SAVINGS', '3.50% p.a. up to Rs 50L, 4.00% above',
 'Total Relationship Value Rs 10L to be maintained. No charges on branch transactions.',
 'Individuals with TRV of Rs 10 lakh or more across deposits and investments.',
 'Dedicated RM, Infinite debit card, airport lounge access, locker discount 50%.',
 'N/A', 'Rs 10L TRV', 'premier savings wealth relationship'),
('SAV-ZERO', 'ABC Zero Balance Digital Savings', 'SAVINGS', '2.75% p.a.',
 'No minimum balance. Physical debit card Rs 199/yr.',
 'Resident Indians 18+, video KYC.', 'Open in 10 minutes via app, virtual debit card.',
 'N/A', 'Nil', 'zero balance digital savings instant'),
('CUR-BIZ', 'ABC Business Current Account', 'CURRENT', 'Non-interest bearing',
 'AMB Rs 25,000. Cash deposit free up to Rs 2L/month, Rs 4 per 1000 thereafter.',
 'Proprietorships, partnerships, LLPs and companies with business registration proof.',
 'Free RTGS/NEFT, bulk payments, GST collection, multi-user net banking.',
 'N/A', 'Rs 25,000 AMB', 'current account business msme company'),
('FD-REG', 'ABC Fixed Deposit', 'FD', '7 days-1 yr: 4.50-6.75%; 1-2 yrs: 7.10%; 2-5 yrs: 7.25%; 5-10 yrs: 7.00%',
 'Premature withdrawal penalty 1% on applicable rate.',
 'Resident individuals, HUFs, companies. Min Rs 10,000.',
 'Loan/overdraft up to 90% of deposit, auto-renewal, monthly/quarterly payout options.',
 '7 days to 10 years', 'Rs 10,000', 'fixed deposit fd term deposit interest rate'),
('FD-SEN', 'ABC Senior Citizen Fixed Deposit', 'FD', 'Additional 0.50% over regular FD rates (up to 7.75%)',
 'Premature withdrawal penalty 0.5%.', 'Resident individuals aged 60+.',
 'Extra rate, monthly interest payout, 15H form facility.',
 '7 days to 10 years', 'Rs 10,000', 'senior citizen fd fixed deposit elderly'),
('FD-TAX', 'ABC Tax Saver Fixed Deposit', 'FD', '7.00% p.a.',
 'No premature withdrawal allowed (5-year lock-in).', 'Resident individuals and HUFs.',
 'Deduction up to Rs 1.5L under Section 80C.', '5 years lock-in', 'Rs 100', 'tax saver fd 80c tax saving'),
('HL-STD', 'ABC Home Loan', 'HOME_LOAN', '8.35% - 9.25% p.a. (repo linked)',
 'Processing fee 0.50% (max Rs 10,000) + GST. No prepayment charges on floating rate.',
 'Salaried/self-employed aged 21-65, min income Rs 25,000/month, CIBIL 700+.',
 'Up to 90% LTV, balance transfer with top-up, doorstep service, 30-year tenure.',
 'Up to 30 years', 'Rs 5 lakh', 'home loan housing property mortgage balance transfer'),
('HL-BT', 'ABC Home Loan Balance Transfer', 'HOME_LOAN', 'From 8.35% p.a.',
 'Processing fee waived for transfers above Rs 30L until 31-Dec.',
 'Existing home loan with 12+ months clean repayment.',
 'Top-up up to Rs 50L at home loan rate.', 'Up to 30 years', 'Rs 10 lakh', 'balance transfer home loan switch top up'),
('PL-STD', 'ABC Personal Loan', 'PERSONAL_LOAN', '10.75% - 16.00% p.a.',
 'Processing fee up to 2% + GST. Foreclosure 4% before 12 EMIs, nil after.',
 'Salaried aged 21-60, min income Rs 25,000/month, 1 yr with current employer.',
 'Instant disbursal for pre-approved customers, no collateral.',
 '12 to 60 months', 'Rs 50,000 - Rs 40 lakh', 'personal loan instant unsecured'),
('CL-NEW', 'ABC New Car Loan', 'CAR_LOAN', '8.75% - 10.50% p.a.',
 'Processing fee Rs 3,500 + GST. Prepayment 5% in first year.',
 'Salaried/self-employed aged 21-65, min income Rs 3L p.a.',
 'Up to 100% on-road funding for select models, 7-year tenure.',
 '12 to 84 months', 'Rs 1 lakh', 'car loan auto vehicle new car'),
('CL-USED', 'ABC Pre-owned Car Loan', 'CAR_LOAN', '11.50% - 14.00% p.a.',
 'Processing fee 1% + GST.', 'Car age + tenure must not exceed 10 years.',
 'Up to 85% of valuation.', '12 to 60 months', 'Rs 1 lakh', 'used car pre-owned second hand loan'),
('CC-MIL', 'ABC Millennia Credit Card', 'CREDIT_CARD', '3.6% per month on revolving balance',
 'Joining/annual fee Rs 1,000 (waived on Rs 1L annual spend).', 'Age 21-40, income Rs 35,000/month.',
 '5% cashback on Amazon/Flipkart/Swiggy, 1% elsewhere, 8 lounge visits/yr.',
 'N/A', 'N/A', 'credit card cashback millennia online shopping'),
('CC-REW', 'ABC Rewards Credit Card', 'CREDIT_CARD', '3.5% per month on revolving balance',
 'Annual fee Rs 500 (waived on Rs 50,000 spend).', 'Age 21-60, income Rs 25,000/month.',
 '4 reward points per Rs 150, fuel surcharge waiver.', 'N/A', 'N/A', 'rewards credit card points fuel'),
('CC-TRV', 'ABC Travel Credit Card', 'CREDIT_CARD', '3.4% per month',
 'Annual fee Rs 2,500. Forex markup 2%.', 'Age 21-65, income Rs 75,000/month.',
 '10X miles on flights/hotels, unlimited domestic lounge, 12 intl lounge visits.',
 'N/A', 'N/A', 'travel credit card miles forex lounge international'),
('CC-INF', 'ABC Infinite Credit Card', 'CREDIT_CARD', '1.99% per month',
 'Annual fee Rs 12,500 (waived on Rs 10L spend). Forex markup 1.99%.',
 'By invitation; income Rs 3L/month or Premier customers.',
 'Unlimited global lounge, golf, concierge, 5 reward points per Rs 150.',
 'N/A', 'N/A', 'infinite premium super premium credit card'),
('INV-MF', 'ABC Mutual Fund SIP', 'INVESTMENT', 'Market linked',
 'No bank charges; fund expense ratios apply.', 'KYC-compliant individuals.',
 'SIPs from Rs 500, 40+ AMCs, goal-based portfolios via app.', 'Flexible', 'Rs 500', 'mutual fund sip investment equity'),
('INV-PPF', 'ABC Public Provident Fund', 'INVESTMENT', '7.10% p.a. (Govt notified)',
 'No charges.', 'Resident Indian individuals.', 'EEE tax status, 80C deduction, partial withdrawal from year 7.',
 '15 years', 'Rs 500/yr', 'ppf public provident fund tax saving'),
('SRV-LCK', 'ABC Safe Deposit Locker', 'SERVICES', 'N/A',
 'Small Rs 2,500/yr, Medium Rs 5,000/yr, Large Rs 10,000/yr (metro) + GST.',
 'Any ABC Bank account holder, subject to availability.', 'Biometric access, 24x7 CCTV, nomination facility.',
 'Annual', 'N/A', 'locker safe deposit'),
('SRV-NRI', 'ABC NRE/NRO Accounts', 'SAVINGS', 'NRE 3.50%, NRO 3.00% p.a.',
 'AMB Rs 10,000.', 'Non-Resident Indians and OCI holders.',
 'Tax-free NRE interest, full repatriation, online remittance.', 'N/A', 'Rs 10,000', 'nri nre nro non resident abroad');

-- ---------- Inbox ----------
INSERT INTO emails (from_email, from_name, subject, body, received_at, priority) VALUES
('rahul.mehta@example.com', 'Rahul Mehta', 'Current balance in my savings account',
 E'Hi Priya,\n\nCould you please let me know the current available balance in my savings account ending 0001? I need to make a large payment this week.\n\nThanks,\nRahul', now() - INTERVAL '5 hours', 'HIGH'),
('prospect.amit@gmail.com', 'Amit Verma', 'Home loan interest rates',
 E'Dear Sir/Madam,\n\nI am planning to buy a flat in Pune worth Rs 90 lakh. What are your current home loan interest rates, processing fees and eligibility criteria?\n\nRegards,\nAmit Verma', now() - INTERVAL '4 hours 40 minutes', 'NORMAL'),
('ananya.iyer@example.com', 'Ananya Iyer', 'Amount debited twice - Croma purchase',
 E'Hello,\n\nI made a UPI payment of Rs 18,999 at Croma yesterday but the amount has been debited twice from my account. Please check and refund the duplicate debit urgently.\n\nAnanya', now() - INTERVAL '4 hours 10 minutes', 'HIGH'),
('meera.joshi@example.com', 'Meera Joshi', 'Home loan outstanding and next EMI',
 E'Hi,\n\nCan you share the outstanding principal on my home loan and the date of my next EMI? I am considering a part-prepayment.\n\nBest,\nMeera', now() - INTERVAL '3 hours 50 minutes', 'NORMAL'),
('neha.kapoor@outlook.com', 'Neha Kapoor', 'Which credit card is best for travel?',
 E'Hi,\n\nI travel internationally 4-5 times a year. Which of your credit cards would you recommend, and what are the annual fees and lounge benefits?\n\nThanks,\nNeha', now() - INTERVAL '3 hours 30 minutes', 'NORMAL'),
('vikram.singh@example.com', 'Vikram Singh', 'Last 10 transactions',
 E'Priya,\n\nPlease send me the last 10 transactions on my savings account. I need them for reconciliation with my CA.\n\nVikram', now() - INTERVAL '3 hours', 'NORMAL'),
('rahul.mehta@example.com', 'Rahul Mehta', 'FD maturing soon - renewal options',
 E'Hi Priya,\n\nI believe one of my fixed deposits is maturing this month. Can you confirm the maturity date and amount? Also let me know if I can renew it.\n\nRahul', now() - INTERVAL '2 hours 45 minutes', 'NORMAL'),
('senior.gupta@yahoo.com', 'R K Gupta', 'Senior citizen FD rates',
 E'Respected Madam,\n\nI am 67 years old. Kindly inform me of the fixed deposit interest rates available for senior citizens and whether monthly interest payout is possible.\n\nThank you,\nR K Gupta', now() - INTERVAL '2 hours 20 minutes', 'NORMAL'),
('fatima.sheikh@example.com', 'Fatima Sheikh', 'Credit card blocked?',
 E'Hi,\n\nMy credit card transaction was declined at a restaurant last night. Is my card blocked? What is my current outstanding and due date?\n\nFatima', now() - INTERVAL '2 hours', 'HIGH'),
('startup.founder@techlabs.io', 'Siddharth Rao', 'Opening a current account for my startup',
 E'Hello,\n\nWe are a newly incorporated private limited company. What documents are required to open a business current account, and what is the minimum balance?\n\nSiddharth\nTechLabs Pvt Ltd', now() - INTERVAL '1 hour 40 minutes', 'NORMAL'),
('sneha.kulkarni@example.com', 'Sneha Kulkarni', 'Personal loan foreclosure',
 E'Dear Priya,\n\nI want to close my personal loan early. How much is outstanding and are there any foreclosure charges?\n\nRegards,\nSneha', now() - INTERVAL '1 hour 20 minutes', 'NORMAL'),
('kavya.reddy@example.com', 'Kavya Reddy', 'Zero balance account for my brother',
 E'Hi,\n\nMy younger brother just turned 18. Do you have a zero balance savings account he can open online? What are the features?\n\nKavya', now() - INTERVAL '1 hour', 'LOW'),
('arjun.nair@example.com', 'Arjun Nair', 'Car loan EMI details',
 E'Hello,\n\nPlease confirm my car loan EMI amount, how many EMIs I have paid and the remaining outstanding.\n\nThanks,\nArjun', now() - INTERVAL '45 minutes', 'NORMAL'),
('nri.deepak@gmail.com', 'Deepak Menon', 'NRE account and repatriation',
 E'Hi team,\n\nI am working in Dubai. I would like to open an NRE account. What is the interest rate and can I repatriate funds fully?\n\nDeepak', now() - INTERVAL '30 minutes', 'NORMAL'),
('rohan.desai@example.com', 'Rohan Desai', 'Account balance and FD summary',
 E'Hi Priya,\n\nCould you share a quick summary of my savings balance and my fixed deposits with you?\n\nRohan', now() - INTERVAL '10 minutes', 'NORMAL');
