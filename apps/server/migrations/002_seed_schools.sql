-- 샘플 데이터. 출시 전 각 학교의 상징 동물/색상을 공식 자료로 검증할 것.
-- 학교 공식 마스코트 이미지는 쓰지 않고, 동물 + 상징색으로 오리지널 캐릭터를 만든다.
INSERT INTO schools (name, animal, color_primary, color_secondary, sprite_set) VALUES
  ('고려대학교', 'tiger', '#8B0029', '#FFFFFF', 'tiger'),
  ('연세대학교', 'eagle', '#003876', '#FFFFFF', 'eagle')
ON CONFLICT (name) DO NOTHING;
