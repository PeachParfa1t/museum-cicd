INSERT INTO collections (name, theme, founded_year, description)
SELECT 'История города', 'Городской быт XIX-XX веков', 1987,
       'Предметы, фотографии и документы, рассказывающие о развитии города.'
WHERE NOT EXISTS (SELECT 1 FROM collections);

INSERT INTO collections (name, theme, founded_year, description)
SELECT 'Театральное наследие', 'История сцены и костюма', 2004,
       'Эскизы, костюмы, афиши и личные вещи артистов.'
WHERE (SELECT COUNT(*) FROM collections) = 1;

INSERT INTO halls (name, floor, capacity, description)
SELECT 'Город и время', 1, 45, 'Постоянная историческая экспозиция.'
WHERE NOT EXISTS (SELECT 1 FROM halls);

INSERT INTO halls (name, floor, capacity, description)
SELECT 'Сцена и закулисье', 2, 30, 'Выставка о театральной жизни региона.'
WHERE (SELECT COUNT(*) FROM halls) = 1;

INSERT INTO employees (full_name, position, email, phone)
SELECT 'Анна Воронцова', 'Главный хранитель', 'vorontsova@museum.local', '+7 900 100-20-30'
WHERE NOT EXISTS (SELECT 1 FROM employees);

INSERT INTO employees (full_name, position, email, phone)
SELECT 'Илья Соколов', 'Экскурсовод', 'sokolov@museum.local', '+7 900 440-11-72'
WHERE (SELECT COUNT(*) FROM employees) = 1;

INSERT INTO events (title, event_date, location, description)
SELECT 'Ночь в музее', '2026-05-16', 'Все залы', 'Вечерние экскурсии и лекции хранителей.'
WHERE NOT EXISTS (SELECT 1 FROM events);

INSERT INTO events (title, event_date, location, description)
SELECT 'История одного костюма', '2026-10-08', 'Сцена и закулисье', 'Кураторская встреча о реставрации сценического костюма.'
WHERE (SELECT COUNT(*) FROM events) = 1;

INSERT INTO exhibits (inventory_number, title, creation_year, material, collection_id, hall_id)
SELECT 'МГ-001', 'Карманные часы купца', 1898, 'Серебро, стекло',
       (SELECT id FROM collections ORDER BY id LIMIT 1),
       (SELECT id FROM halls ORDER BY id LIMIT 1)
WHERE NOT EXISTS (SELECT 1 FROM exhibits);

INSERT INTO exhibits (inventory_number, title, creation_year, material, collection_id, hall_id)
SELECT 'ТН-014', 'Эскиз костюма к спектаклю', 1976, 'Бумага, акварель',
       (SELECT id FROM collections ORDER BY id LIMIT 1 OFFSET 1),
       (SELECT id FROM halls ORDER BY id LIMIT 1 OFFSET 1)
WHERE (SELECT COUNT(*) FROM exhibits) = 1;
