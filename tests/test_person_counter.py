from person_counter import count_people


def test_count_people_counts_only_person_class():
    assert count_people([0, 0, 56, 2, 1]) == 2


def test_count_people_handles_empty_detections():
    assert count_people([]) == 0


def test_count_people_accepts_tensor_like_values():
    class Value:
        def int(self):
            return self

        def tolist(self):
            return [0, 56, 0]

    assert count_people(Value()) == 2


def test_count_people_rejects_none_as_zero():
    assert count_people(None) == 0
