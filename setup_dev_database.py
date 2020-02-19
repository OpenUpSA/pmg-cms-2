from pmg.models import db
from tests.fixtures import *


class UserData(DataSet):
    class admin_user:
        email = "admin"
        name = "Admin"
        password = "admin"
        active = True
        roles = [RoleData.admin, RoleData.editor]
        confirmed = True


if __name__ == "__main__":
    db.create_all()
    db_fixture = dbfixture.data(
        HouseData,
        MinisterData,
        CommitteeData,
        CommitteeMeetingData,
        BillTypeData,
        BillStatusData,
        BillData,
        CallForCommentData,
        TabledCommitteeReportData,
        PartyData,
        ProvinceData,
        MemberData,
        CommitteeQuestionData,
        EventData,
        FeaturedData,
        PageData,
        PostData,
        RoleData,
        UserData,
        MembershipTypeData,
        MembershipData,
    )
    db_fixture.setup()
