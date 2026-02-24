from larrak2.machining.cost_model import calculate_tolerance_budget, calculate_tooling_cost


def test_cost():
    print("Testing Tooling Cost...")
    # 1. Standard Tool exists (e.g. Feature Size = 4.0mm -> Tool D=4.0)
    cost, standard = calculate_tooling_cost(4.0, 0.0)
    print(f"Feature 4.0mm (Outer): Cost={cost:.2f}, Standard={standard}")
    # Expected: Best tool 4.0. Cost = 10/4 = 2.5.

    # 2. Non-standard (e.g. 0.5mm feature)
    cost, standard = calculate_tooling_cost(0.5, 0.0)
    print(f"Feature 0.5mm (Outer): Cost={cost:.2f}, Standard={standard}")
    # Expected: No tool < 0.5? Wiat. 0.5mm feature means Radius 0.25??
    # min_feature_size_outer_mm = 2 * BMaxSurvivable.
    # If BMax = 0.25, Feature = 0.5.
    # My logic: valid_tools <= max_d_outer.
    # Smallest standard tool is 1.0mm.
    # So 0.5mm feature -> No standard tool.
    # Cost = 5 + 10/0.5 = 25.0. False.

    # 3. Hole (e.g. 12mm hole)
    cost, standard = calculate_tooling_cost(20.0, 12.0)
    print(f"Feature 20.0mm (Outer), Hole 12.0mm: Cost={cost:.2f}, Standard={standard}")
    # Expected: Outer fits 20mm tool. Inner fits 12mm tool.
    # Logic: best_tool = min(20, 12) = 12.
    # Cost = 10/12 = 0.83.

    print("\nTesting Tolerance Budget...")
    # 1. Tight constraints (Thin ligament 0.2mm)
    req, pen = calculate_tolerance_budget(0.2, 5.0)
    print(f"Ligament 0.2mm: Req={req:.4f}, Penalty={pen:.2f}")
    # Expected: t_prof ~ 0.005. t_thick=0.2. t_bore~0.05. Total ~ 0.255.
    # Budget 0.5. Result < Budget. Penalty > 0.

    # 2. Loose constraints (Ligament 3.0mm)
    req, pen = calculate_tolerance_budget(3.0, 5.0)
    print(f"Ligament 3.0mm: Req={req:.4f}, Penalty={pen:.2f}")
    # Expected: t_prof=0.1. Total ~ 0.35.
    # Still < 0.5?
    # Maybe my t_thick default (0.2) is small?
    # Total = 0.1 + 0.2 + 0.05 = 0.35.
    # Budget 0.5.
    # So even "Loose" gear fails the budget?
    # This means the budget (0.5) is very generous (easy to achieve?) No.
    # "Maximize tolerances ... minimum 0.5mm".
    # User said: "Total variation is 0.31, failing the minimum of 0.5".
    # This implies 0.31 is TOO TIGHT. We want > 0.5.
    # Correct.
    # So if Req=0.35, Penalty should be applied (force looser).


if __name__ == "__main__":
    test_cost()
