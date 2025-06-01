-- Vytvoření tabulky uživatelů (User)
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- Automatický čítač pro id
    first_name TEXT NOT NULL,            -- Jméno uživatele
    last_name TEXT NOT NULL,             -- Příjmení uživatele
    workplace TEXT DEFAULT 'Not specified',  -- Pracoviště uživatele (výchozí hodnota "Not specified")
    salary REAL NOT NULL                 -- Plat uživatele
);

-- Vytvoření tabulky výdajů (Expense)
CREATE TABLE IF NOT EXISTS expense (
    id INTEGER PRIMARY KEY AUTOINCREMENT,   -- Automatický čítač pro id
    category TEXT NOT NULL,                 -- Kategorie výdaje
    amount REAL NOT NULL,                   -- Částka výdaje
    description TEXT,                       -- Popis výdaje
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Datum vytvoření výdaje (výchozí hodnota aktuální čas)
    user_id INTEGER NOT NULL,               -- Cizí klíč pro uživatele
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE  -- Spojení s uživatelem, při smazání uživatele se smažou i výdaje
);

-- Vytvoření indexu pro tabulku výdajů (pro rychlejší vyhledávání podle user_id)
CREATE INDEX IF NOT EXISTS idx_user_id ON expense(user_id);

-- Ukázková data pro testování (nepovinné)
-- Vložení uživatelů
INSERT INTO user (first_name, last_name, workplace, salary) 
VALUES 
('John', 'Doe', 'Company XYZ', 50000),
('Jane', 'Smith', 'Company ABC', 45000),
('Сука', 'Підр', 'Not specified', 1000);  -- Používáme výchozí hodnotu pro workplace

-- Vložení výdajů pro uživatele
INSERT INTO expense (category, amount, description, user_id) 
VALUES
('Food', 200, 'Nákupy potravin', 1),
('Transport', 50, 'Městská doprava', 1),
('Entertainment', 150, 'Vstupenky na koncert', 2);
