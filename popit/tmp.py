from popit import PopIt


api = PopIt(instance='test-pmg-za',
            hostname='popit.mysociety.org',
            # port=3000,
            api_version='v0.1',
            user='',
            password='')


if __name__ == "__main__":

    new_person = api.persons.post({'name': 'Albert Keinstein'})
    print(new_person)

    # get the id of the newly created item
    id = new_person['result']['_id']