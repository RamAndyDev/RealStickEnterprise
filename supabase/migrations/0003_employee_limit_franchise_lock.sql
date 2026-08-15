-- Serialize active-employee counting per franchise so concurrent inserts
-- cannot bypass the existing 10-employee (franchise.employee_limit) rule.
-- Replaces the helper used by profiles_enforce_role_and_employee_limit.
-- Does not change the limit itself: only active EMPLOYEE rows count.

create or replace function public.enforce_profile_role_franchise_rules()
returns trigger
language plpgsql
as $$
declare
  employee_count integer;
  max_employees integer;
begin
  if new.role = 'SYSTEM_ADMIN' then
    if new.franchise_id is not null then
      raise exception 'SYSTEM_ADMIN profiles must not belong to a franchise';
    end if;
  elsif new.role in ('FRANCHISE_OWNER', 'EMPLOYEE') then
    if new.franchise_id is null then
      raise exception '% profiles must belong to a franchise', new.role;
    end if;
  end if;

  if new.role = 'EMPLOYEE' and new.is_active then
    perform 1
    from public.franchises f
    where f.id = new.franchise_id
    for update;

    select f.employee_limit
    into max_employees
    from public.franchises f
    where f.id = new.franchise_id;

    if max_employees is null then
      raise exception 'Franchise not found for employee profile';
    end if;

    select count(*)
    into employee_count
    from public.profiles
    where franchise_id = new.franchise_id
      and role = 'EMPLOYEE'
      and is_active = true
      and id is distinct from new.id;

    if employee_count >= max_employees then
      raise exception 'Maximum of % active employees allowed per franchise', max_employees;
    end if;
  end if;

  return new;
end;
$$;
