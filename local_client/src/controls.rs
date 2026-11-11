use sdl3::keyboard::Keycode;

#[derive(Default)]
pub struct Controls {
    held: Vec<Keycode>,
}

fn direction(key: Keycode) -> Option<&'static str> {
    match key {
        Keycode::Space | Keycode::C => Some("outward"),
        Keycode::V => Some("inward_fast"),
        _ => None,
    }
}

impl Controls {
    pub fn key(&mut self, key: Keycode, down: bool) -> Option<&'static str> {
        let command = direction(key)?;
        let position = self.held.iter().position(|held| *held == key);
        match (down, position) {
            (true, None) => {
                self.held.push(key);
                Some(command)
            }
            (false, Some(index)) => {
                self.held.remove(index);
                Some(
                    self.held
                        .last()
                        .and_then(|key| direction(*key))
                        .unwrap_or("inward"),
                )
            }
            _ => None,
        }
    }

    pub fn focus_lost(&mut self) -> &'static str {
        self.held.clear();
        "inward"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn held_key_priority_repeat_release_and_focus_loss() {
        let mut controls = Controls::default();
        let mut commands: Vec<_> = [
            (Keycode::C, true),
            (Keycode::C, true),
            (Keycode::V, true),
            (Keycode::V, false),
            (Keycode::C, false),
            (Keycode::Space, true),
            (Keycode::V, true),
        ]
        .into_iter()
        .filter_map(|(key, down)| controls.key(key, down))
        .collect();
        commands.push(controls.focus_lost());
        assert_eq!(
            commands,
            [
                "outward",
                "inward_fast",
                "outward",
                "inward",
                "outward",
                "inward_fast",
                "inward"
            ]
        );
        assert_eq!(controls.key(Keycode::V, false), None);
        assert_eq!(controls.key(Keycode::A, true), None);
    }
}
