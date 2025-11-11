from ci_agent.agent import build_call

print(build_call('CI_compare', entities=['Mo Studio']))
print(build_call('CI_compare', entities=['A','B']))
print(build_call('CI_landscape', entities=['SoloCo']))
print(build_call('CI_matrix', entities=['SoloCo'], criteria=['Speed','TCO']))
