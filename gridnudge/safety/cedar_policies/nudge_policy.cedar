// GridNudge AWS Cedar Policy
// Authoritative authorization rules for EV charging persuasion nudges

// Permit only when all physical, operational, and user preference constraints hold
permit (
  principal,
  action == Action::"SendNudge",
  resource
) when {
  context.optedOut == false &&
  context.quietHours == false &&
  context.nudgesToday < 3 &&
  context.journeyConfLbBps >= 9000 &&
  context.invariantsOk == true &&
  context.vehicleSupportsPlan == true
};

// Belt-and-braces: hard deny on unsafe journey regardless of other permits
forbid (
  principal,
  action == Action::"SendNudge",
  resource
) when {
  context.journeyConfLbBps < 9000
};
