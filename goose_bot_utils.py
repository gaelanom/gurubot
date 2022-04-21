import random


async def roll_result(limit, rolls):
    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    print(result)
    no_spaces = result.replace(" ", "")
    dice = no_spaces.split(",")
    roll_sum = 0
    for element in dice:
        if isinstance(element, int) or element.isdigit():
            roll_sum += int(element)
    roll_sum = str(roll_sum)
    result = result + ' (' + roll_sum + ')'
    return result


async def prettify_roles(role_list, prefix):
    pretty_roles = prefix + "\n"
    for r in role_list:
        r = '`' + r.name.replace("@", "") + '`'
        pretty_roles += r + ","
    return pretty_roles[:-1]


async def prettify_role(role_name: str):
    role_name = '`' + role_name.name.replace("@", "") + '`'
    return role_name
